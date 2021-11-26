#!/usr/bin/env python
# Copyright 2021 AstroLab Software
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
"""Compute statistics for a given observing night
"""
import pyspark.sql.functions as F

from fink_broker.sparkUtils import init_sparksession

from fink_broker.parser import getargs
from fink_broker.loggingUtils import get_fink_logger, inspect_application

from fink_broker.science import extract_fink_classification

from fink_science.utilities import concat_col
from fink_science.asteroids.processor import roid_catcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    args = getargs(parser)

    # Initialise Spark session
    spark = init_sparksession(name="statistics_{}".format(args.night))

    # Logger to print useful debug statements
    logger = get_fink_logger(spark.sparkContext.appName, args.log_level)

    # debug statements
    inspect_application(logger)

    year = args.night[:4]
    month = args.night[4:6]
    day = args.night[6:8]

    print('Statistics for {}/{}/{}'.format(year, month, day))

    input_raw = '{}/year={}/month={}/day={}'.format(
        'ztf_alerts/raw', year, month, day)
    input_science = '{}/year={}/month={}/day={}'.format(
        'ztf_alerts/science_reprocessed', year, month, day)

    df_raw = load_parquet_files(input_raw)
    df_sci = load_parquet_files(input_science)

    df_raw = df_raw.cache()
    df_sci = df_sci.cache()

    # Number of alerts
    n_raw_alert = df_raw.count()
    n_sci_alert = df_sci.count()

    out_dic['raw'] = n_raw_alert
    out_dic['sci'] = n_sci_alert

    # matches with SIMBAD
    n_simbad = df_sci.select('cdsxmatch')\
        .filter(df_sci['cdsxmatch'] != 'Unknown')\
        .count()

    out_dic['simbad'] = n_simbad

    # Alerts with a close-by candidate host-galaxy
    list_simbad_galaxies = [
        "galaxy",
        "Galaxy",
        "EmG",
        "Seyfert",
        "Seyfert_1",
        "Seyfert_2",
        "BlueCompG",
        "StarburstG",
        "LSB_G",
        "HII_G",
        "High_z_G",
        "GinPair",
        "GinGroup",
        "BClG",
        "GinCl",
        "PartofG",
    ]

    n_simbad_gal = df_sci.select('cdsxmatch')\
        .filter(df_sci['cdsxmatch'].isin(list_simbad_galaxies))\
        .count()

    out_dic['simbad_gal'] = n_simbad_gal

    # to account for schema migration
    if 'knscore' not in df_sci.columns:
        df_sci = df_sci.withColumn('knscore', F.lit(-1.0))
    # 12/08/2021
    if 'tracklet' not in df_sci.columns:
        df_sci = df_sci.withColumn('tracklet', F.lit(''))

    df_class = df_sci.withColumn(
        'class',
        extract_fink_classification(
            df_sci['cdsxmatch'],
            df_sci['roid'],
            df_sci['mulens.class_1'],
            df_sci['mulens.class_2'],
            df_sci['snn_snia_vs_nonia'],
            df_sci['snn_sn_vs_all'],
            df_sci['rfscore'],
            df_sci['candidate.ndethist'],
            df_sci['candidate.drb'],
            df_sci['candidate.classtar'],
            df_sci['candidate.jd'],
            df_sci['candidate.jdstarthist'],
            df_sci['knscore'],
            df_sci['tracklet']
        )
    )

    out_class = df_class.groupBy('class').count().collect()
    out_class_ = [o.asDict() for o in out_class]
    out_class_ = [list(o.values()) for o in out_class_]
    for kv in out_class_:
        out_dic[kv[0]] = kv[1]

    # Number of fields
    n_field = df_raw.select('candidate.field').distinct().count()

    out_dic['fields'] = n_field

    # number of measurements per band
    n_g = df_sci.select('candidate.fid').filter('fid == 1').count()
    n_r = df_sci.select('candidate.fid').filter('fid == 2').count()

    out_dic['n_g'] = n_g
    out_dic['n_r'] = n_r

    # Number of exposures
    n_exp = df_raw.select('candidate.jd').distinct().count()

    out_dic['exposures'] = n_exp

    out_dic['night'] = 'ztf_{}'.format(args.night)

    print(out_dic)


if __name__ == "__main__":
    main()