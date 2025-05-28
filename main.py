import json
from socket import socket, AF_INET, SOCK_STREAM
import sqlite3
import re


def connection_db():
    conn = sqlite3.connect("data_base.db")
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
        request = r.decode("utf-8").split('\r\n')
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

        method, path, headers, body = parse(request_data)

        if not method:
            client_conn.send(create_response(400, json.dumps({"error": "Invalid request"})))
            return

        print(f"Получен запрос {method} {path} от {addr[0]}")

        handle, params = find_methods(method, path)
        if handle:
            try:
                if params:
                    status_code, response_body = handle(method, path, headers, body, **params)
                else:
                    status_code, response_body = handle(method, path, headers, body)
                client_conn.send(create_response(status_code, response_body))
            except Exception as err:
                print(f"Ошибка обработчика: {err}")
                err_response = json.dumps({"error": "Internal server error"})
                client_conn.send(create_response(500, err_response))
        else:
            methods = ["GET", "POST", "PATCH", "DELETE"]
            client_conn.send(create_response(405, json.dumps({"error": "Method not allowed",
                                                              "allowed methods": methods})))


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


def handle_main(method, path, headers, body):
    info = {
        "message": "Ура, заработало",
        "endpoints": {
            "/about": "Информация о том что поддерживает сервер",
            "/clients": "Управление клиентами"
        }
    }
    print("Пользователь находится на главной странице")
    return 200, json.dumps(info)


def handle_about(method, path, headers, body):
    info = {
        "message": "Сервер умеет: работать с GET, POST, DELETE, PATCH"
    }
    print("Пользователь на странице about")
    return 200, json.dumps(info)


def handle_get_all_db(method, path, headers, body):
    try:
        cursor = db_connect.cursor()
        cursor.execute("SELECT * FROM clients")
        clients = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        print("Пользователь сделал GET запрос ко всей базе данных")
        return 200, json.dumps(clients)
    except Exception as err:
        print(f"Ошибка базы данных: {err}")
        return 500, json.dumps({"error": "database error"})


def handle_get_db(method, path, headers, body, id):
    try:
        cursor = db_connect.cursor()
        cursor.execute(f"Select id, name from clients where id = ?", (id,))
        client = cursor.fetchone()
        print("Пользователь сделал GET запрос по определенному id")
        if client:
            return 200, json.dumps({"id": client[0], "name": client[1]})
        else:
            return 404, json.dumps({"error": "Client not found"})
    except Exception as err:
        print(f"Ошибка базы данных: {err}")
        return 500, json.dumps({"error": "database error"})


def handle_post(method, path, headers, body):
    try:
        cursor = db_connect.cursor()
        data = json.loads(body)
        if "name" not in data:
            return 400, json.dumps({"error": "Name is requered"})
        elif "id" not in data:
            return 400, json.dumps({"error": "Id is requered"})
        cursor.execute("INSERT INTO clients VALUES (?, ?)", (data["id"], data["name"]))
        db_connect.commit()
        print(f"Пользователь добавил запись в таблицу с id: {data["id"]} и name: {data["name"]}")
        return 201, json.dumps({"message": "Client created"})
    except json.JSONDecodeError:
        return 400, json.dumps({"error": "Invalid JSON format"})
    except Exception as err:
        print(f"Ошибка базы данных: {err}")
        return 500, json.dumps({"error": "database error"})


def handle_patch(method, path, headers, body, id):
    try:
        data = json.loads(body)
        if "name" not in data:
            return 400, json.dumps({"error": "Name is requered"})
        cursor = db_connect.cursor()
        cursor.execute("UPDATE clients SET name = ? WHERE id = ?", (data['name'], id))
        if cursor.rowcount == 0:
            return 404, json.dumps({"error": "Client not found"})
        db_connect.commit()
        print(f"Пользователь изменил запись в таблицу с id: {id} изменив name: {data["name"]}")
        return 200, json.dumps({"message": "Client updated"})
    except json.JSONDecodeError:
        return 400, json.dumps({"error": "Invalid JSON format"})
    except Exception as err:
        print(f"Ошибка базы данных: {err}")
        return 500, json.dumps({"error": "database error"})


def handle_delete(method, path, headers, body, id):
    try:
        cursor = db_connect.cursor()
        cursor.execute("DELETE FROM clients WHERE id = ?", (id,))
        if cursor.rowcount == 0:
            return 404, json.dumps({"error": "Client not found"})
        db_connect.commit()
        print(f"Пользователь удалил запись с id: {id}")
        return 204, ""
    except Exception as err:
        print(f"Ошибка базы данных: {err}")
        return 500, json.dumps({"error": "database error"})


ROUTES = {
    "GET": {
        "/": handle_main,
        "/about": handle_about,
        "/clients": handle_get_all_db,
        re.compile(r"^/clients/(\d+)$"): handle_get_db
    },
    "POST": {
        "/clients": handle_post
    },
    "PATCH": {
        re.compile(r"/clients/(\d+)"): handle_patch
    },
    "DELETE": {
        re.compile(r"/clients/(\d+)"): handle_delete
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
