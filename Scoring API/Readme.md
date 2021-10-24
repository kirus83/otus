🔖Домашнее задание выполнено для курса <code>["Python Developer. Professional"](https://otus.ru/lessons/python-professional/)</code>
# Scoring API
Реализация  системы валидации запросов ĸ HTTP API сервиса сĸоринга.
# Струĸтура запроса
`{"account": "<имя компании партнера>", "login": "<имя пользователя>", "method": "<имя метода>", "token": "
<аутентификационный токен>", "arguments": {<словарь с аргументами вызываемого метода>}}`
# Пример запроса
`'{"account": "horns&hoofs", "login": "h&f", "method":
"online_score", "token":
"55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd
"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name":
"Ступников", "birthday": "01.01.1990", "gender": 1}}'`
# Python 
Использовалась версия 3.9.6
# api.py
Модуль с api для валидации HTTP запросов.
### Пример запуска
<code>$ curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method":
"online_score", "token":
"55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd
"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name":
"Ступников", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/
</code>
# test.py
Скрипт для тестирования функциональности системы валидации HTTP запросов. 
### Пример запуска
<code>python -m unittest test</code>
