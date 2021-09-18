#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import gzip
import json
import logging
import re
import statistics
import sys
from configparser import RawConfigParser
from logging import config
from pathlib import Path
from typing import Dict, Generator, List

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

DEFAULT_CONFIG = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': './reports',
    'LOG_DIR': './log'
}
# Regular expression for parsing date in nginx log name
DATE_PATTERN = re.compile(r'.*(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})')
# Regular expression for parsing row in nginx log
ROW_PATTERN = re.compile(
    r'(?P<remote_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s(?P<remote_user>\S+)\s+(?P<http_x_real_ip>\S+)\s+'
    r'\[(?P<time_local>.+)\]\s+"(?P<request>.*?)"\s+(?P<status>\d{3})\s+(?P<body_bytes_sent>\d+)\s+'
    r'"(?P<http_referer>.+)"\s+"(?P<http_user_agent>.+)"\s+"(?P<http_x_forwarded_for>.+)"\s+'
    r'"(?P<http_X_REQUEST_ID>.+)"\s+"(?P<http_X_RB_USER>.+)"\s+(?P<request_time>.+)'
)


LOGGER = None


def init_logger(config_path: str) -> None:
    """
    This function initiates logging parameters
    """
    logging.config.fileConfig(config_path)
    global LOGGER
    LOGGER = logging.getLogger('ParserWork')


def parse_config_args() -> Dict:
    """
    This function creates config args for the script.
    :return: file_config(dict): A dictionary with config values.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='./log_analyzer.conf', help='path to config')
    try:
        args = parser.parse_args()
    except:
        sys.stdout.write('Configuration file is missed in params!')
        return dict()
    config_path = args.config
    if not Path(config_path).exists():
        sys.stdout.write('Configuration file {} is not exists!'.format(config_path))
        return dict()
    init_logger(config_path)
    config_parser = RawConfigParser()
    config_parser.read(config_path)
    file_config = config_parser._sections.get('log_analyzer', {})
    file_config = {config_param_name.upper(): config_param_value for config_param_name, config_param_value in
                   file_config.items()}
    for item in set(DEFAULT_CONFIG.keys()).difference(set(file_config.keys())):
        file_config[item] = DEFAULT_CONFIG[item]

    return file_config


def parse_logs(log_path: str,
               log_pattern: str,
               file_config: Dict):
    """
    This function function gets a list of the last LOGS_COUNT sorted log files
    by date in their name with the extension gz or plain and the template
    :return: log_files(list): List of files.
    """
    log_files = Path(log_path).glob(log_pattern)
    try:
        # Getting sorted by date in file name ext with gz or plain list type of WindowsPath
        log_files = [sorted_file for sorted_file in
                     sorted((file for file in log_files if file.suffix == '.gz' or file.suffix == '.plain'),
                            key=lambda el: el.stem.split('.')[-1], reverse=True)][:int(file_config['LOGS_COUNT'])]
        return log_files
    except ValueError:
        LOGGER.error('Getting nginx log files in {} is failed!'.format(log_path))
        return []


def parse_log(file: str):
    """
    This function parsing nginx log file
    :return:
        urls_list(list): list of urls.
        sum_requests(int): sum of requests
        sum_requests_time(float): sum of requests time
    """
    urls_list = {}
    sum_requests = 0
    sum_requests_time = 0
    log_rows = read_log(file)
    try:
        log_row = next(log_rows)
        while log_row:
            data = re.search(ROW_PATTERN, log_row)
            calculate_url_statistics(urls_list, data.groupdict(0))
            sum_requests += 1
            sum_requests_time += float(data.groupdict(0)['request_time']) or .0
            log_row = next(log_rows)
    except:
        log_row = None
    return urls_list, sum_requests, sum_requests_time


def read_log(file_name: str) -> Generator:
    """
    This generator function opening and read file
    :return: row: row of file
    """
    if file_name.endswith('gz'):
        log = gzip.open(file_name, mode='rt', encoding='utf-8')
    else:
        log = open(file_name, 'r')
    for row in log:
        yield row
    log.close()


def calculate_url_statistics(urls_list: List[str],
                             log_line: Dict):
    """
    This function calculating statistics for each unique url
    :return:
    """
    url = log_line['request']
    rt = float(log_line['request_time']) or 0.
    if url not in urls_list:
        urls_list[url] = {}
        urls_list[url]['url'] = url
        urls_list[url]['med'] = []
        urls_list[url]['med'].append(rt)
        urls_list[url]['count'] = 1
        urls_list[url]['time_max'] = rt
        urls_list[url]['time_sum'] = round(rt, 3)
    else:
        urls_list[url]['count'] += 1
        urls_list[url]['med'].append(rt)
        if rt > float(log_line['request_time']):
            urls_list[url]['time_max'] = rt
        urls_list[url]['time_sum'] = round(urls_list[url]['time_sum'] + rt, 3)


def enrich_url_statistics(urls_list: List[str],
                          sum_req: float,
                          sum_req_time: float):
    """
    This function enriching statistics for each unique url
    :return: urls_list(list): list of urls with statistics
    """
    for el in urls_list:
        try:
            el['time_perc'] = round(el['time_sum'] / (sum_req_time / 100), 3)
            el['time_avg'] = round(round(el['time_sum'] / (el['count'] / 100), 3) / 100, 3)
            el['count_perc'] = round(el['count'] / (sum_req / 100), 3)
            el['med'] = round(statistics.median(el['med']), 3)
        except KeyError:
            LOGGER.error(
                'This columns is absent in the log: time_sum,med and count!'
            )
    return urls_list


def create_report(report: List[str], report_path: Path):
    """
    This function create report
    :return:
    """
    try:
        with open('./templates/report.html', 'r', encoding='utf-8') as f:
            template = f.read()
    except:
        LOGGER.error('Error while opening report.html')
        return

    template = template.replace('$table_json', json.dumps(report))
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(template)
    except:
        LOGGER.error('Error while writing report.html')
        return


def main(file_config: Dict):
    """
    This function processes logs
    :return:
    """
    # Initiating configuration parameters
    logs_dir = file_config['LOG_DIR']
    report_template = 'report-{Y}.{m}.{d}.html'
    log_template = 'nginx-access-ui*'
    reports_dir = Path(file_config['REPORT_DIR'])
    report_size = file_config['REPORT_SIZE']
    # Get last log file
    files = parse_logs(logs_dir, log_template, file_config)
    # Parsing log files
    if len(files) > 0:
        for file in files:
            # Set report name and dir
            report_name = report_template.format(**DATE_PATTERN.search(file.name).groupdict())
            report_path = reports_dir / report_name
            report_path.parent.mkdir(exist_ok=True, parents=True)
            # If report already exists then exit with msg
            if Path(report_path).exists():
                LOGGER.info('Report {} is completed early!'.format(report_path))
            else:
                urls_list, sum_requests, sum_requests_time = parse_log(str(file))
                # Sorting urls list on max time_sum for max report_size
                urls_list = sorted(urls_list.values(), key=lambda el: el.get('time_sum', 0), reverse=True)[
                            :int(report_size)]
                # Get statistics
                urls_list = enrich_url_statistics(urls_list, sum_requests, sum_requests_time)
                # Create report
                create_report(urls_list, report_path)
                LOGGER.info('The report {} is done'.format(report_path))
    else:
        LOGGER.info('Log file or dir {} is not founded!'.format(logs_dir))


if __name__ == '__main__':
    init_config = parse_config_args()
    if init_config:
        main(init_config)
