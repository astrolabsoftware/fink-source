#!/usr/bin/env python
# Copyright 2019 AstroLab Software
# Author: Abhishek Chauhan
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

"""Distribute the alerts to users

1. Use the Alert data that is stored in the Science database (HBase)
2. Serialize into Avro
3. Publish to Kafka Topic(s)
"""

import argparse
import json

from fink_broker.parser import getargs
from fink_broker.sparkUtils import init_sparksession
from fink_broker.distributionUtils import get_kafka_df

def main():
    parser = argparse.ArgumentParser(description = __doc__)
    args = getargs(parser)

    # Get or create a Spark Session
    spark = init_sparksession(
        name = "distribution", shuffle_partitions = 2, log_level = "ERROR")

    # Read the catalog file generated by raw2science
    science_db_catalog = args.science_db_catalog
    with open(science_db_catalog) as f:
        catalog = json.load(f)

    # Read the HBase and create a DataFrame
    df = spark.read.option("catalog", catalog)\
        .format("org.apache.spark.sql.execution.datasources.hbase")\
        .load()

    # Get the DataFrame for publishing to Kafka (avro serialized)
    df_kafka = get_kafka_df(df, args.distribution_schema)

    # Publish to a test topic (Ensure that the topic exists on the Kafka Server)
    topic = "distribution_test"

    df_kafka\
        .write\
        .format("kafka")\
        .option("kafka.bootstrap.servers", "localhost:9093")\
        .option("topic", topic)\
        .save()

if __name__ == "__main__":
    main()
