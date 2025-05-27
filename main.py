import json
from socket import socket, AF_INET, SOCK_STREAM
import sqlite3
import re


def connection_db():
    conn = sqlite3.connect("data_base")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS clients(
                   id INTEGER,
                   name TEXT
                   )
                   ''')
    conn.commit()
    print("Создание и инициализация базы данных")
    return conn


db_connect = connection_db()


def parse(r):
    try:
        request = r.split('\r\n')
        if not request[0]:
            return None, None, None, None
        method, path, _ = request[0].split(" ")
        headers = {}
        body = None
        body_started = False
        for line in request[1:]:
            if not line and not body_started:
                body_started = True
                continue
            if not body_started:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key] = value
            else:
                body = line

        return method, path, headers, body
    except Exception as err:
        print(f"Ошибка обработки запроса: {err}")
        return None, None, None, None


def create_response(status_code, body=None, headers=None):
    status_text = {
        200: 'OK',
        201: 'Created',
        204: 'No Content',
        400: 'Bad Request',
        404: 'Not Found',
        405: 'Method Not Allowed',
        500: 'Internal Server Error'
    }.get(status_code, 'Unknown')

    response = f"HTTP/1.1 {status_code} {status_text}\r\n"
    response += f"Content-Type: application/json\r\n"

    if headers:
        for key, value in headers.value():
            response += f"{key}: {value}\r\n"
    if body:
        response += f"Content-Length: {len(body)}\r\n"
        response += "\r\n"
        response += body
    else:
        response += "\r\n"

    return response.encode("utf-8")


def handle_client(client_conn, addr):
    try:
        request_data = client_conn.recv(1024)
        if not request_data:
            return

        method, path, headers, body = parse(request_data.decode())

        if not method:
            client_conn.send(create_response(400, json.dumps({"error": "Invalid request"})))
            return

        print(f"Получен запрос {method} {path} от {addr[0]}")

    except Exception as err:
        print(f"Ошибка при обработке {err}")
        err_response = json.dumps({"error": "Internal server error"})
        client_conn.send(create_response(500, err_response))
    finally:
        client_conn.close()


def start_server():
    server = socket(AF_INET, SOCK_STREAM)
    server.bind(('localhost', 12000))
    server.listen(5)

    print("Запускаем сервер (в данном случае на 127.0.0.1:12000)")

    try:
        while True:
            conn_client, addr = server.accept()
            print(f"Слушаем {addr}")
            handle_client(conn_client, addr)
    except KeyboardInterrupt:
        print("Выключаем сервер и закрываем базу данных")
        db_connect.close()
        server.close()


def handle_main():
    ...


def handle_about():
    ...


def handle_get_all_db():
    ...


def handle_get_db():
    ...


def handle_post():
    ...


def handle_patch():
    ...


def handle_delete():
    ...


ROUTES = {
    "GET": {
        "/": handle_main,
        "/about": handle_about,
        "clients": handle_get_all_db,
        re.compile(r"clients/(\d+)"): handle_get_db
    },
    "POST": {
        "clients": handle_post
    },
    "PATCH": {
        re.compile(r"clients/(\d+)"): handle_patch
    },
    "DEL": {
        re.compile(r"clients/(\d+)"): handle_delete
    }
}


def find_methods(method, path):
    if method not in ROUTES:
        return None, None

    for route, handle in ROUTES[method].items():
        if isinstance(route, str):
            if route == path:
                return handle, {}
        elif isinstance(route, re.Pattern):
            find = route.match(path)
            if find:
                return handle, {"id": int(find.group(1))}
    return None, None

if __name__ == "__main__":
    start_server()
