# Nginx log analyzer
Парсер nginx логов. Создание отчёта в папку reports с именем report-Y.m.d.html В нём содержится список url со статистическими характеристиками по каждому из них.
# Формат лога
`'$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" $status $body_bytes_sent "$http_referer" ' '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" $request_time'`
# Пример лога
`1.169.137.128 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/group/1823183/banners HTTP/1.1" 200 1002 "-" "Configovod" "-" "1498697423-2118016444-4708-9752777" "712e90144abee9" 0.680`
# Статистические данные для url
- count - сĸольĸо раз встречается URL, абсолютное значение 
- count_perc - сĸольĸо раз встречается URL, в процентнах относительно общего числа запросов 
- time_sum - суммарный $request_time для данного URL'а, абсолютное значение 
- time_perc - суммарный $request_time для данного URL'а, в процентах относительно общего $request_time всех запросов 
- time_avg - средний $request_time для данного URL'а 
- time_max - маĸсимальный $request_time для данного URL'а 
- time_med - медиана $request_time для данного URL'а
# Python 
Использовалась версия 3.9.6
# log_analyzer.py
Скрипт парсера логов. Принимает на вход параметр --config с именем конфигурационного файла.
Если параметр не задан, то используется файл конфигурации по умолчанию log_analyzer.conf
### Пример запуска
<code>python log_analyzer --config log_analyzer.conf</code>
# test_log_analyzer.py
Скрипт для тестирования функциональности парсера логов. 
### Пример запуска
<code>python -m unittest test_log_analyzer</code>
