#!/usr/bin/env python
# Copyright 2019-2024 AstroLab Software
# Author: Julien Peloton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Update the (tmp) science database from the raw database alert data.

Step 1: Connect to the raw database
Step 2: Filter alerts based on instrumental or environmental criteria.
Step 3: Run processors (aka science modules) on alerts to generate added value.
Step 4: Push alert data into the tmp science database (parquet)

See http://cdsxmatch.u-strasbg.fr/ for more information on the SIMBAD catalog.
"""

from pyspark.sql import functions as F

import argparse
import time

from fink_broker import __version__ as fbvsn
from fink_broker.parser import getargs
from fink_broker.spark_utils import init_sparksession
from fink_broker.spark_utils import connect_to_raw_database
from fink_broker.logging_utils import get_fink_logger, inspect_application
from fink_broker.partitioning import convert_to_datetime, convert_to_millitime

from fink_broker.science import apply_science_modules
from fink_broker.science import apply_science_modules_elasticc

from fink_science import __version__ as fsvsn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    args = getargs(parser)

    if args.night == "elasticc":
        tz = "UTC"
    else:
        tz = None

    # Initialise Spark session
    spark = init_sparksession(
        name="raw2science_{}_{}".format(args.producer, args.night),
        shuffle_partitions=2,
        tz=tz
    )

    # Logger to print useful debug statements
    logger = get_fink_logger(spark.sparkContext.appName, args.log_level)

    # debug statements
    inspect_application(logger)

    # data path
    rawdatapath = args.online_data_prefix + '/raw'
    scitmpdatapath = args.online_data_prefix + '/science'
    checkpointpath_sci_tmp = args.online_data_prefix + '/science_checkpoint/{}'.format(args.night)

    if args.producer == "elasticc":
        df = connect_to_raw_database(rawdatapath, rawdatapath, latestfirst=False)
    else:
        # assume YYYYMMHH
        df = connect_to_raw_database(
            rawdatapath + '/{}'.format(args.night),
            rawdatapath + '/{}'.format(args.night),
            latestfirst=False
        )

        # Add ingestion timestamp
        df = df.withColumn(
            'brokerStartProcessTimestamp',
            convert_to_millitime(
                df['candidate.jd'],
                F.lit('jd'),
                F.lit(True)
            )
        )

    # Add library versions
    df = df.withColumn('fink_broker_version', F.lit(fbvsn))\
        .withColumn('fink_science_version', F.lit(fsvsn))

    # Switch publisher
    df = df.withColumn('publisher', F.lit('Fink'))

    # Apply science modules
    if "candidate" in df.columns:
        # Apply quality cuts
        logger.info("Applying quality cuts")
        df = df.filter(df["candidate.nbad"] == 0).filter(df["candidate.rb"] >= 0.55)

        df = apply_science_modules(df, args.noscience)

        # Add ingestion timestamp
        df = df.withColumn(
            'brokerEndProcessTimestamp',
            convert_to_millitime(
                df['candidate.jd'],
                F.lit('jd'),
                F.lit(True)
            )
        )

        # Append new rows in the tmp science database
        countquery = df\
            .writeStream\
            .outputMode("append") \
            .format("parquet") \
            .option("checkpointLocation", checkpointpath_sci_tmp) \
            .option("path", scitmpdatapath)\
            .trigger(processingTime='{} seconds'.format(args.tinterval)) \
            .start()

    elif 'diaSource' in df.columns:
        df = apply_science_modules_elasticc(df)
        timecol = "diaSource.midPointTai"
        converter = lambda x: convert_to_datetime(x, F.lit("mjd"))

        # re-create partitioning columns if needed.
        if 'timestamp' not in df.columns:
            df = df\
                .withColumn("timestamp", converter(df[timecol]))

        if "year" not in df.columns:
            df = df\
                .withColumn("year", F.date_format("timestamp", "yyyy"))

        if "month" not in df.columns:
            df = df\
                .withColumn("month", F.date_format("timestamp", "MM"))

        if "day" not in df.columns:
            df = df\
                .withColumn("day", F.date_format("timestamp", "dd"))

        # Append new rows in the tmp science database
        countquery = df\
            .writeStream\
            .outputMode("append") \
            .format("parquet") \
            .option("checkpointLocation", checkpointpath_sci_tmp) \
            .option("path", scitmpdatapath)\
            .partitionBy("year", "month", "day") \
            .trigger(processingTime='{} seconds'.format(args.tinterval)) \
            .start()

    # Keep the Streaming running until something or someone ends it!
    if args.exit_after is not None:
        time.sleep(args.exit_after)
        countquery.stop()
        logger.info("Exiting the raw2science service normally...")
    else:
        # Wait for the end of queries
        spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
