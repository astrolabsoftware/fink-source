# Copyright 2024 AstroLab Software
# Author: Roman Le Montagner
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
"""Utilities for Fink-MM integration"""
import os
import time

from fink_mm.distribution.distribution import grb_distribution_stream
from fink_broker.loggingUtils import get_fink_logger


def mm2distribute(spark, config, args):
    """Launch the streaming between ZTF and GCN streams"""
    mm_data_path = config["PATH"]["online_grb_data_prefix"]
    kafka_broker = config["DISTRIBUTION"]["kafka_broker"]
    username_writer = config["DISTRIBUTION"]["username_writer"]
    password_writer = config["DISTRIBUTION"]["password_writer"]

    year, month, day = args.night[0:4], args.night[4:6], args.night[6:8]
    basepath = os.path.join(
        mm_data_path, "online", "year={}/month={}/day={}".format(year, month, day)
    )
    checkpointpath_mm = os.path.join(mm_data_path, "mm_distribute_checkpoint")

    logger = get_fink_logger()
    wait = 5
    while True:
        try:
            logger.info("successfully connect to the MM database")
            # force the mangrove columns to have the struct type
            static_df = spark.read.parquet(basepath)

            path = basepath
            df_grb_stream = (
                spark.readStream.format("parquet")
                .schema(static_df.schema)
                .option("basePath", basepath)
                .option("path", path)
                .option("latestFirst", True)
                .load()
            )
            break

        except Exception:
            logger.info("Exception occured: wait: {}".format(wait), exc_info=1)
            time.sleep(wait)
            wait *= 1.2 if wait < 60 else 1
            continue

    df_grb_stream = (
        df_grb_stream.drop("brokerEndProcessTimestamp")
        .drop("brokerStartProcessTimestamp")
        .drop("brokerIngestTimestamp")
    )

    stream_distribute_list = grb_distribution_stream(
        df_grb_stream,
        static_df,
        checkpointpath_mm,
        args.tinterval,
        kafka_broker,
        username_writer,
        password_writer,
    )

    return stream_distribute_list