from socket import socket, AF_INET, SOCK_STREAM
import sqlite3


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
    request = r.split('\r\n')
    print(request)


def start_server():
    server = socket(AF_INET, SOCK_STREAM)
    server.bind(('localhost', 12000))
    server.listen(1)

    print("Запускаем сервер (в данном случае на 127.0.0.1:12000)")

    try:
        while True:
            conn_client, addr = server.accept()
            print(f"Слушаем {addr}")
    except KeyboardInterrupt:
        print("Выключаем сервер и закрываем базу данных")
        db_connect.close()
        server.close()

if __name__ == "__main__":
    start_server()