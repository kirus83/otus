#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import gzip
import re
import os
import logging
import glob
import argparse
import statistics
import json
from collections import namedtuple
from configparser import RawConfigParser
from collections import defaultdict

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}
# Регулярка для парсинга даты в логе
date_pattern = re.compile(r'.*(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})')
# Регулярка для паринга строки в логе
row_pattern = re.compile(
    r'(?P<remote_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s(?P<remote_user>\S+)\s+(?P<http_x_real_ip>\S+)\s+'
    r'\[(?P<time_local>.+)\]\s+"(?P<request>.*?)"\s+(?P<status>\d{3})\s+(?P<body_bytes_sent>\d+)\s+'
    r'"(?P<http_referer>.+)"\s+"(?P<http_user_agent>.+)"\s+"(?P<http_x_forwarded_for>.+)"\s+'
    r'"(?P<http_X_REQUEST_ID>.+)"\s+"(?P<http_X_RB_USER>.+)"\s+(?P<request_time>.+)'
)


# Формирование параметров из конфигурационного файла и настроек по умолчанию
def config_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='./log_analyzer.conf', help='path to config')
    try:
        args = parser.parse_args()
    except:
        sys.stdout.write('Configuration file is missed in params!')
        return
    config_path = args.config
    if not os.path.exists(config_path):
        sys.stdout.write('Configuration file {} is not exists!'.format(config_path))
        return
    config_parser = RawConfigParser()
    config_parser.read(config_path)
    f_config = config_parser._sections.get('log_analyzer', {})
    f_config = dict([[k.upper(), v] for k, v in f_config.items()])
    for item in set(config.keys()).difference(set(f_config.keys())):
        f_config[item] = config[item]

    if not f_config.get('LOG_FILE'):
        logging.basicConfig(
            format='[%(asctime)s] %(levelname).1s %(message)s',
            datefmt='%Y.%m.%d %H:%M:%S',
            stream=sys.stdout,
            level=logging.INFO
        )
    else:
        logging.basicConfig(
            format='[%(asctime)s] %(levelname).1s %(message)s',
            datefmt='%Y.%m.%d %H:%M:%S',
            filename=f_config.get('LOG_FILE'),
            level=logging.INFO
        )
    return f_config


# Получаем лог с самой свежей датой и расширением gz или plain
def f_max(items, key=lambda x: x):
    current = None
    if len(items) != 0:
        current = items[0]
        for item in items:
            if key(item) > key(current) and (str(item).endswith('gz') or str(item).endswith('plain')):
                current = item
    return current


# Поиск лога
def log_finder(log_path, log_pattern, dt_pattern=date_pattern):
    log_files = glob.glob(os.path.join(log_path, log_pattern))
    try:
        log_file = f_max(log_files, key=lambda file: dt_pattern.match(file).group(0))
        return log_file
    except ValueError:
        logging.error('Get nginx log file in {} is failed!'.format(log_path))
        return


# Чтение лога
def log_reader(file_name):
    if file_name.endswith('gz'):
        log = gzip.open(file_name, mode='rt', encoding='utf-8')
    else:
        log = open(file_name, "r")
    for row in log:
        yield row
    log.close()


# Формирование словаря запросов и количественными характеристиками
def get_urls(urls_list, log_line):
    url = log_line['request']
    rt = float(log_line['request_time']) or float(0)
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


# Формирование статистических параметров для запросов
def get_urls_stat(urls_list, sum_req, sum_req_time):
    for el in urls_list:
        try:
            el['time_perc'] = round(el['time_sum'] / (sum_req_time / 100), 3)
            el['time_avg'] = round(round(el['time_sum'] / (el['count'] / 100), 3) / 100, 3)
            el['count_perc'] = round(el['count'] / (sum_req / 100), 3)
            el['med'] = round(statistics.median(el['med']), 3)
        except KeyError:
            logging.error(
                'This columns is absent in the log: time_sum,med and count!'
            )
    return json.dumps(urls_list)


# Создание отчёта из "рыбы"
def create_report(report, report_path):
    try:
        with open('./report.html', 'r', encoding='utf-8') as f:
            template = f.read()
    except:
        logging.error('Error while opening report.html')

    template = template.replace('$table_json', report)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(template)
    except:
        logging.error('Error while writing report.html')


# Обработка лога
def main(f_config):
    # Инициация парамтеров конфигурации
    logs_dir = f_config['LOG_DIR']
    report_template = 'report-{Y}.{m}.{d}.html'
    log_template = 'nginx-access-ui*'
    reports_dir = f_config['REPORT_DIR']
    report_size = f_config['REPORT_SIZE']
    # Получаем самый "свежий лог"
    file = log_finder(logs_dir, log_template)
    # Проходим строки лога
    if file:
        # Формируем название отчёта и полный путь к нему
        report_name = report_template.format(**date_pattern.search(file).groupdict())
        report_path = os.path.join(reports_dir, report_name)
        # Если отчёт с сформированным именем уже существует, значит выходим
        if os.path.exists(report_path):
            logging.info('Report {} is completed early!'.format(report_path))
            return

        urls_list = {}
        sum_requests = 0
        sum_requests_time = 0
        l_rows = log_reader(file)
        try:
            l_row = next(l_rows)
            while l_row:
                data = re.search(row_pattern, l_row)
                get_urls(urls_list, data.groupdict(0))
                sum_requests += 1
                sum_requests_time += float(data.groupdict(0)['request_time']) or float(0)
                l_row = next(l_rows)
        except:
            l_row = None
        # Отсеем запросы по максимальному времени выполнения не более заданного количества
        urls_list = sorted(urls_list.values(), key=lambda el: el.get('time_sum', 0), reverse=True)[
                    :int(report_size)]
        # По отсортированным запросам получим статистику
        urls_list = get_urls_stat(urls_list, sum_requests, sum_requests_time)
        # Сформируем файл отчёта
        create_report(urls_list, report_path)
        print('The report {} is done'.format(report_path))
    else:
        logging.info('Log file or dir {} is not founded!'.format(logs_dir))


if __name__ == "__main__":
    init_config = config_args()
    if init_config:
        main(init_config)
