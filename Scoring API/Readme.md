🔖Домашнее задание выполнено для курса <code>["Python Developer. Professional"](https://otus.ru/lessons/python-professional/)</code>
# Scoring API
Реализация  системы валидации запросов ĸ HTTP API сервиса сĸоринга.
# Струĸтура запроса
`{"account": "<имя компании партнера>", "login": "<имя пользователя>", "method": "<имя метода>", "token": "
<аутентификационный токен>", "arguments": {<словарь с аргументами вызываемого метода>}}`
# Пример запроса
`'{"account": "horns&hoofs", "login": "h&f", "method":
"online_score", "token":
"e6f5540b9c571683d644a7f22389fb354dded449c1e2ac0340ea1c01bfc8b962544063900d2f684f166e5e494c69a3d44a65334e187ac969996a1d501ecb7cf9",
"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name":
"Ступников", "birthday": "01.01.1990", "gender": 1}}'`
# Python 
Использовалась версия 3.9.6
# api.py
Модуль с api для валидации HTTP запросов.
### Пример запуска
#### Linux
<code>$ curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method":
"online_score", "token":
"e6f5540b9c571683d644a7f22389fb354dded449c1e2ac0340ea1c01bfc8b962544063900d2f684f166e5e494c69a3d44a65334e187ac969996a1d501ecb7cf9",
"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name":
"Ступников", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/
</code>
#### Windows(PowerShell)
<code>$params = @"
{
"account": "horns&hoofs",
"login": "h&f",
"method": "online_score",
"token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
"arguments": {
"phone": "79175002040",
"email": "stupnikov@otus.ru",
"first_name": "Stanislav",
"last_name": "Stupnikov",
"birthday": "01.01.1990",
"gender": "male"
}
}
"@ | ConvertFrom-Json</code>

<code>Invoke-WebRequest -Uri http://localhost:8080/method -Method POST -Body ($params|ConvertTo-Json) -ContentType "application/json"</code>
# test.py
Скрипт для тестирования функциональности системы валидации HTTP запросов. 
### Пример запуска
<code>python -m unittest test</code>
