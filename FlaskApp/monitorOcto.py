#!/usr/bin/python2.7

from flask import Flask, render_template, redirect, url_for, request, session, abort
from flask import jsonify
from flask import request
from flask import Response
from time import gmtime, strftime
from datetime import datetime, timedelta
import json as simplejson
import requests
import threading
import collections
import os
import json
import sys
from sqlalchemy.orm import sessionmaker
from tabledef import *



engine = create_engine('sqlite:///tutorial.db', echo=True)

app = Flask(__name__)

orig_stdout = sys.stdout
f = open('outPython.txt', 'w')
sys.stdout = f

# Direccion sobre la que corre el Octoprint dentro del servidor.
# host = "http://127.0.0.1"
# Direccion sobre la que corre el Octoprint.
host = "http://192.168.1.200"

# Archivo files API Octoprint.
files = "files"

# Archivo printer API Octoprint.
printer = "printer"

# Archivo job API Octoprint (para monitorizar las impresiones en curso).
job = "job"

# Direccion de la API para conectar o desconectar las impresoras mediante una peticion POST
conn = "connection"

maquinas = list()
# Lista en las que se guardan los datos utiles que vamos a mostrar.
valoresFiles = list()
valoresPrinter = dict()
valoresJob = dict()

# Diccicionarios con clave el id de la maquina y valor los datos de cada maquina.
datosFinalesFiles = dict()
datosFinalesPrinter = dict()
datosFinalesJob = dict()

datosJsonPrinter = dict()
datosJsonJob = dict()

# Un diccionario para guardar los errores que se hayan podido producir en las peticiones a la API.
errores = dict()

# Array con los identificadores de las maquinas y las direcciones con el proxy para poner los enlaces en el index
nombres = dict()
nombresOrdenados = dict()


# Rellenamos los valores que necesitamos, ya que en caso de un cambio API la aplicacion siga funcionando.
valoresPrinter["Pausa"] = "-"
valoresPrinter["Imprimiendo"] = "-"
valoresPrinter["Lista"] = "-"
valoresPrinter["Estado"] = "-"
valoresPrinter["TempCamaActual"] = "-"
valoresPrinter["TempCamaFijada"] = "-"
valoresPrinter["TempHottendActual"] = "-"
valoresPrinter["TempHottendFijada"] = "-"
valoresPrinter["CamaDisponible"] = "-"

valoresJob["TiempoEstimadoImpresion"] = "-"
valoresJob["Nombre"] = "-"
valoresJob["TiempoUltimaImpresion"] = "-"
valoresJob["Porcentaje"] = "-"
valoresJob["TiempoImpresion"] = "-"
valoresJob["TiempoRestante"] = "-"
valoresJob["Estado"] = "-"

# Cargamos los datos de las impreoras desde el archivo csv
reader = open("./datosImpresoras.csv", "r")
for row in reader:
    maquinas.append(row.strip().split(";"))
# Borramos la primera fila que contiene los nombres
maquinas.pop(0)

# Array con los identificadores de las maquinas y las direcciones con el proxy para poner los enlaces en el index

reader2 = open("./nombres.csv", 'r')
n = 0
for row in reader2:
    elemento = row.strip().split(";")
    nombres["maq" + str(n)] = {"Nombre": str(elemento[0]), "direccion": str(elemento[1]), "numMaquina": str(n)}
    n = n + 1
nombres.pop("maq0")

for element in range(0, len(maquinas)):
    maquina = maquinas[element][1]
    datosFinalesJob[maquina] = valoresJob
    datosFinalesPrinter[maquina] = valoresPrinter


# Funcion que devuelve los datos de impresora (temperaturas de cama y extrusor).
def pide_datos_printer(datos):
    # Diccionario temporal en el que iremos guardando nuestros valores utiles.
    valores_printer = dict()

    # Pausa
    try:
        valores_printer["Pausa"] = str(datos["state"]["flags"]["paused"])
    except:
        valores_printer["Pausa"] = "-"

    # Imprimiendo
    try:
        valores_printer["Imprimiendo"] = str(datos["state"]["flags"]["printing"])
    except:
        valores_printer["Imprimiendo"] = "-"

    # Lista
    try:
        valores_printer["Lista"] = str(datos["state"]["flags"]["ready"])
    except:
        valores_printer["Lista"] = "-"

    # Estado Impresora (conectada o no)
    try:
        valores_printer["Estado"] = str(datos["state"]["text"])
    except:
        valores_printer["Estado"] = "-"

    # Comprobamos que la impresora este conectada mediante las lecturas de temperatura
    try:
        if len(datos["temperature"]) == 0:
            print("Conflicto con la API en Printer (impresora desconectada)")
        else:
            # Comprobamos que la impresora tiene como caracteristica la cama caliente.
            if "bed" in datos["temperature"]:

                # Temperatura actual de la cama
                valores_printer["TempCamaActual"] = str(datos["temperature"]["bed"]["actual"])

                # Temperatura fijada de la cama
                valores_printer["TempCamaFijada"] = str(datos["temperature"]["bed"]["target"])

                # Temperatura actual del extrusor
                valores_printer["TempHottendActual"] = str(datos["temperature"]["tool0"]["actual"])

                # Temperatura fijada de extrusor
                valores_printer["TempHottendFijada"] = str(datos["temperature"]["tool0"]["target"])
            else:
                # Temperatura actual del extrusor
                valores_printer["TempHottendActual"] = str(datos["temperature"]["tool0"]["actual"])

                # Temperatura fijada de extrusor
                valores_printer["TempHottendFijada"] = str(datos["temperature"]["tool0"]["target"])
                valores_printer["CamaDisponible"] = str("No")
    except:
        if len(datos["temperature"]) == 0:
            print("Conflicto con la API en Printer (impresora desconectada)")
        else:
            # Comprobamos que la impresora tiene como caracteristica la cama caliente.
            if "bed" in datos["temperature"]:

                # Temperatura actual de la cama
                valores_printer["TempCamaActual"] = "-"

                # Temperatura fijada de la cama
                valores_printer["TempCamaFijada"] = "-"

                # Temperatura actual del extrusor
                valores_printer["TempHottendActual"] = "-"

                # Temperatura fijada de extrusor
                valores_printer["TempHottendFijada"] = "-"
            else:
                # Temperatura actual del extrusor
                valores_printer["TempHottendActual"] = "-"

                # Temperatura fijada de extrusor
                valores_printer["TempHottendFijada"] = "-"
                valores_printer["CamaDisponible"] = str("No")


    # Devolvemos el diccionario con los datos de cada maquina.
    return valores_printer


# Funcion que devuelve los datos de la impresion en curso (Timepo, Timeleft, Porcentaje completado...).
def pide_datos_job(datos):
    # Diccionario temporal en el que guardaremos nuestros datos utiles.
    valores_job = dict()

    # Comprabamos que el tiempo estimado de impresion no es None, y entonces cambiamos el formato a uno legible.
    try:
        if datos["job"]["estimatedPrintTime"] is None:
            valores_job["TiempoEstimadoImpresion"] = str(datos["job"]["estimatedPrintTime"])
        else:
            tiempo = datos["job"]["estimatedPrintTime"]
            m, s = divmod(tiempo, 60)
            h, m = divmod(m, 60)
            # Hacemos la conversion y lo guardamos en nuestro diccionario en horas, minutos y segundos.
            valores_job["TiempoEstimadoImpresion"] = "%d:%02d:%02d" % (h, m, s)
    except:
            valores_job["TiempoEstimadoImpresion"] = "-"


    # Nombre del archivo que esta imprimiendo
    try:
        valores_job["Nombre"] = str(datos["job"]["file"]["name"])
    except:
        valores_job["Nombre"] = "-"

    # Tiempo que duro la ultima impresion y hacemos la misma conversion de antes para que los datos sean legibles.
    try:
        if datos["job"]["lastPrintTime"] is None:
            valores_job["TiempoUltimaImpresion"] = str(datos["job"]["lastPrintTime"])
        else:
            tiempo = datos["job"]["lastPrintTime"]
            m, s = divmod(tiempo, 60)
            h, m = divmod(m, 60)
            valores_job["TiempoUltimaImpresion"] = "%d:%02d:%02d" % (h, m, s)
    except:

        if datos["job"]["lastPrintTIme"] is None:
            valores_job["TiempoUltimaImpresion"] = str(datos["job"]["lastPrintTIme"])
        else:
            tiempo = datos["job"]["lastPrintTIme"]
            m, s = divmod(tiempo, 60)
            h, m = divmod(m, 60)
            valores_job["TiempoUltimaImpresion"] = "%d:%02d:%02d" % (h, m, s)


    # Porcetaje de impresion que se ha completado
    try:
        valores_job["Porcentaje"] = str(datos["progress"]["completion"])
    except:
        valores_job["Porcentaje"] = "-"

    # Tiempo que lleva de impresion (pieza actual). Hacemos la misma coversion anterior.
    try:
        if datos["progress"]["printTime"] is None:
            valores_job["TiempoImpresion"] = str(datos["progress"]["printTime"])
        else:
            tiempo = datos["progress"]["printTime"]
            m, s = divmod(tiempo, 60)
            h, m = divmod(m, 60)
            valores_job["TiempoImpresion"] = "%d:%02d:%02d" % (h, m, s)
    except:
        valores_job["TiempoImpresion"] = "-"

    # Tiempo que le queda a la impresion actual. Hacemos la misma coversion anterior.
    try:
        if datos["progress"]["printTimeLeft"] is None:
            valores_job["TiempoRestante"] = str(datos["progress"]["printTimeLeft"])
        else:
            tiempo = datos["progress"]["printTimeLeft"]
            m, s = divmod(tiempo, 60)
            h, m = divmod(m, 60)
            valores_job["TiempoRestante"] = "%d:%02d:%02d" % (h, m, s)
        # Estado de la impresora
        valores_job["Estado"] = str(datos["state"])
    except:
        valores_job["Estado"] = "-"
    # Devolvemos el diccionario con los datos de cada maquina.
    return valores_job


# Funcion que hace las peticiones a la API de cada maquina para obtener el JSON files
# def requestFiles():
# 	for i in range(0, len(maquinas)):
# 		maquina = maquinas[i]
# 		urlstring = str(host + ":" + maquina[0] + "/api/" + files + "?apikey=" + maquina[2])
# 		resp = requests.get(url=urlstring)

# 		try:
# 			#data = simplejson.loads(resp)
# 			data = resp.json()
# 		except Exception as e:

# 			strfallo = "Error en i= %d: %s"
# 			print (strfallo %(i, str(e)))
# 			print("resp del if: " + str(resp))

# 			if resp.status_code == 204:
# 				errores[maquina[1]]="La respuesta de la API no tiene contenido"
# 			elif resp.status_code == 409:
# 				#No hace falta puesto que ya sale el estado de la impresora en otra variable.
# 				errores[maquina[1]]="La impresora no esta operativa"
# 			elif resp.status_code == 404:
# 				errores[maquina[1]]="No hay comunicacion por parte del servidor"
# 			elif resp.status_code == 200:
# 				print("La respuesta es correcta")
# 				#Seguramente se tendra que comentar, se usa a modo debug
# 				datosJson.append(str(data.content()))
# 			#else:
# 				#errores[maquina[1]]= "Hay algun error desconocido"
# 		else:
# 			datosFinalesFiles[maquina[1]] = pideDatosFiles(data,maquina[1])		

# Funcion que hace las peticiones a la API de cada maquina para obtener el JSON printer
def request_printer():
    for i in range(0, len(maquinas)):
        maquina = maquinas[i]
        urlstring = str(host + ":" + maquina[0] + "/api/" + printer + "?apikey=" + maquina[2])
        # Direccion con la que haremos la peticion GET
        try:
            resp = requests.get(url=urlstring)
            # Control de errores (se pueden comentar)
            # print ("resp: "+str(resp))
            # print("status code: " + str(resp.status_code))
            # print("tipo status code: " + str(type(resp.status_code)))
            # print("tipo de resp: " + str(type(resp)))
            # print ("datos resp = " + str(resp.content))
            # print ("datos resp tipo = " + str(type(resp.content)))

            # Parseamos la respuesta para que sea JSON.
            data = resp.json()


        except Exception as e:
            strfallo = "Error en Printer cuando i= %d: %s"
            print (strfallo % (i, str(e)))
            print("resp del if Printer: " + str(resp))

            # Controlamos los posibles errores que nos pueden dar y
            # los capturamos para que la aplicacion siga en funcionamiento,
            # a pesar de que una maquina pueda fallar.
            if resp is None:
                errores[maquina[1]] = "El servicio de Octoprint no esta operativo"

            else:
                if resp.status_code not in (204, 409, 404, 200):
                    # if resp.status_code == 204:
                    # errores[maquina[1]] = "La respuesta de la API no tiene contenido -> CODE 204"
                    # elif resp.status_code == 409:
                    # No hace falta puesto que ya sale el estado de la impresora en otra variable.
                    # errores[maquina[1]] = "La impresora no esta operativa -> CODE 409"
                    # elif resp.status_code == 404:
                    # servidor = "No hay comunicacion por parte del servidor -> CODE 404"
                    # errores[maquina[1]] = servidor
                    # elif resp.status_code == 200:
                    # errores[maquina[1]] = "La respuesta es correcta -> CODE 200"
                    # Seguramente se tendra que comentar, se usa a modo debug
                    # datos_json.append(str(data.content()))

                    code = resp.status_code
                    errores[maquina[1]] = str(" Hay algun error desconocido -> " + str(code))
                    logError(errores)
                    errores.clear()

        else:  # Else del try
            datosFinalesPrinter[maquina[1]] = pide_datos_printer(data)


# Funcion que hace las peticiones a la API de cada maquina para obtener el JSON job
def request_job():
    for i in range(0, len(maquinas)):
        maquina = maquinas[i]
        urlstring = str(host + ":" + maquina[0] + "/api/" + job + "?apikey=" + maquina[2])
        # Direccion con la que haremos la peticion GET
        try:
            resp = requests.get(url=urlstring)
            # Parseamos la respuesta para que sea JSON.
            data = resp.json()


        except Exception as e:

            if resp == None:
                errores[maquina[1]] = "El servicio de Octoprint no esta operativo"
            else:

                strfallo = "Error en Job cuando i= %d: %s"
                print (strfallo % (i, str(e)))
                print("resp del if Job: " + str(resp))

                if resp.status_code not in (204, 409, 404, 200):


                #if resp.status_code == 204:
                    #errores[maquina[1]] = "La respuesta de la API no tiene contenido -> CODE 204"
                #elif resp.status_code == 409:
                    # No hace falta puesto que ya sale el estado de la impresora en otra variable.
                    #errores[maquina[1]] = "La impresora no esta operativa -> CODE 409"
                #elif resp.status_code == 404:
                    #servidor = "No hay comunicacion por parte del servidor -> CODE 404"
                    #errores[maquina[1]] = servidor
                #elif resp.status_code == 200:
                    #errores[maquina[1]] = "La respuesta es correcta -> CODE 200"
                # Seguramente se tendra que comentar, se usa a modo debug
                # datos_json.append(str(data.content()))

                    code = resp.status_code
                    errores[maquina[1]] = str(" Hay algun error desconocido -> " + str(code))
                    logError(errores)
                    errores.clear()


        else:  # Else del try
            datosFinalesJob[maquina[1]] = pide_datos_job(data)

# Ruta para llamar a la funcion que conecta las maquinas
@app.route("/conectar")
# Funcion que conecta las maquinas.
def conectar():
    # Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
    id_maq = request.args.get("maq", default=-1, type=int)
    # print("id maquina: "+ str(id_maq))

    # Sino le pasas nada por parametro, pondra por defecto -1 y significa que hay que conectar todas las maquinas.
    if id_maq != -1:
        maquina = maquinas[id_maq - 1]
        print("Entra en el else:")
        headers = {'Content-Type': 'application/json', 'X-Api-Key': maquina[2]}
        data = '{"command": "connect"}'
        url_conectar = str(host + ":" + maquina[0] + "/api/" + conn)
        requests.post(url_conectar, data=data, headers=headers)

    # Para pruebas
    # print("request else: " + str(peticion))
    # print("status code else: " + str(peticion.status_code))
    # print("tipo status code else: " + str(type(peticion.status_code)))
    # print("tipo de request else: " + str(type(peticion)))
    # print("datos request else = " + str(peticion.content))
    # print("datos request tipo else = " + str(type(peticion.content)))

    # Despues de conectar un maquina devolvemos el main para
    # que vuelva a cargar la pagina principal con todos los datos.
    return main()


# Ruta para llamar a la funcion que desconecta las maquinas
@app.route("/desconectar")
# Funcion que desconecta las maquinas.
def desconectar():
    # Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
    id_maq = request.args.get("maq", default=-1, type=int)
    # print("id maquina: " +str (id_maq))

    # Sino le pasas nada por parametro, pondra por defecto -1 y significa que hay que desconectar todas las maquinas.
    if id_maq != -1:
        maquina = maquinas[id_maq - 1]
        print("Entra en el else:")
        headers = {'Content-Type': 'application/json', 'X-Api-Key': maquina[2]}
        data = '{"command": "disconnect"}'
        url_conectar = str(host + ":" + maquina[0] + "/api/" + conn)
        requests.post(url_conectar, data=data, headers=headers)

    # Despues de conectar un maquina devolvemos el main
    # para que vuelva a cargar la pagina principal con todos los datos.
    return main()


# Ruta para llamar a la funcion que imprime en cada maquina
@app.route("/imprimir")
def imprimir():
    # Ejemplo de direccion http://192.168.1.185:8050/imprimir?maq=1

    # Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
    id_maq = request.args.get("maq", default=-1, type=int)
    # print("id maquina: " +str (id_maq))
    if id_maq != -1:
        maquina = maquinas[id_maq - 1]
        print("Maquina: " + str(maquina))
        headers = {'Content-Type': 'application/json', 'X-Api-Key': maquina[2]}
        data = '{"command": "start"}'
        url_conectar = str(host + ":" + maquina[0] + "/api/" + job)
        # print(str(url_conectar))
        requests.post(url_conectar, data=data, headers=headers)

    return main()

# Ruta para llamar a la funcion que imprime en cada maquina
@app.route("/reanudar")
def reanudar():
    # Ejemplo de direccion http://192.168.1.185:8050/reanudar?maq=1

    # Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
    id_maq = request.args.get("maq", default=-1, type=int)
    # print("id maquina: " +str (id_maq))
    if id_maq != -1:
        maquina = maquinas[id_maq - 1]
        print("Maquina: " + str(maquina))
        headers = {'Content-Type': 'application/json', 'X-Api-Key': maquina[2]}
        data = '{"command": "pause", "action": "resume"}'
        url_conectar = str(host + ":" + maquina[0] + "/api/" + job)
        requests.post(url_conectar, data=data, headers=headers)

    return main()

# Ruta para llamar a la funcion que imprime en cada maquina
@app.route("/pausar")
def pausar():
    # Ejemplo de direccion http://192.168.1.185:8050/pausar?maq=1

    # Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
    id_maq = request.args.get("maq", default=-1, type=int)
    # print("id maquina: " +str (id_maq))
    if id_maq != -1:
        maquina = maquinas[id_maq - 1]
        print("Maquina: " + str(maquina))
        headers = {'Content-Type': 'application/json', 'X-Api-Key': maquina[2]}
        data = '{"command": "pause", "action": "pause"}'
        url_conectar = str(host + ":" + maquina[0] + "/api/" + job)
        requests.post(url_conectar, data=data, headers=headers)

    return main()

# Ruta para llamar a la funcion que imprime en cada maquina
@app.route("/cancelar")
def cancelar():
    # Ejemplo de direccion http://192.168.1.185:8050/cancelar?maq

    # Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
    id_maq = request.args.get("maq", default=-1, type=int)
    # print("id maquina: " +str (id_maq))
    if id_maq != -1:
        maquina = maquinas[id_maq - 1]
        print("Maquina: " + str(maquina))
        headers = {'Content-Type': 'application/json', 'X-Api-Key': maquina[2]}
        data = '{"command": "cancel"}'
        url_conectar = str(host + ":" + maquina[0] + "/api/" + job)
        requests.post(url_conectar, data=data, headers=headers)

    return main()


@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    error = None
    if request.method == 'POST':
        POST_USERNAME = str(request.form['username'])
        POST_PASSWORD = str(request.form['password'])

        Session = sessionmaker(bind=engine)
        s = Session()
        query = s.query(User).filter(User.username.in_([POST_USERNAME]), User.password.in_([POST_PASSWORD]))
        result = query.first()
        if result:
            print("Username" + str(POST_USERNAME))
            session['logged_in'] = True
            if POST_USERNAME == "admin":
                session['admin'] = True
            elif POST_USERNAME == "operador":
                session['operador'] = True
            elif POST_USERNAME == "visor":
                session['visor'] = True
            return main()
        else:
            error = 'Invalid Credentials. Please try again.'
            print("error" + str(error))
            print("Las credenciales son incorrectas")
            print("Resultado" + str(result))
            print("Usuario: " + str(request.form['username']))
            print("Pass: " + str(request.form['password']))

    return render_template('login.html', error=error)


@app.route("/logout")
def logout():
    session['logged_in'] = False
    session['admin'] = False
    session['operador'] = False
    session['visor'] = False
    return main()


@app.route("/update")
def update():
    request_printer()
    request_job()


    datos = {"maq1": dict(), "maq2": dict(), "maq3": dict(), "maq4": dict(), "maq5": dict(), "maq6": dict(), "maq7": dict()}
    #print ("JSONIFY" + str(jsonify(get_json_job())))
    #print ("A PELO EL JSON: " + str(get_json_job()))

    #print ("IMPRIMIMOS LA VARIABLE" + str(json_job))
    #print (datosFinalesJob)
    #print(datosFinalesPrinter)


    for i in datosFinalesPrinter.keys():
        for j in datosFinalesJob.keys():
            #print("IIIII: " + i)
            #print("JJJJJJ: " + j)
            #print(datos[i])
            if i == j:
                for x in datosFinalesPrinter[i]:
                    print(datosFinalesPrinter[i][x])
                    datos[i][x] = datosFinalesPrinter[i][x]
                for y in datosFinalesJob[i]:
                    datos[i][y] = datosFinalesJob[i][y]





    nombres_ordenados = collections.OrderedDict(sorted(nombres.items()))
    datos_finales_job_ordenados = collections.OrderedDict(sorted(datosFinalesJob.items()))
    datos_finales_printer_ordenados = collections.OrderedDict(sorted(datosFinalesPrinter.items()))

    #print (datos_finales_printer_ordenados)
    #print(datos_finales_job_ordenados)

    #print(datos)

    datosOrdenados = collections.OrderedDict(sorted(datos.items()))
    #print("Datos Completos: " + str(datosOrdenados))


    #print ("Datos Finales: " + str(datos_finales_printer_ordenados))
    #print ("Datos JOB: " + str(datos_finales_job_ordenados))

    json_printer = json.dumps(datosFinalesPrinter)
    json_job = json.dumps(datos_finales_job_ordenados)

    return (json_printer, json_job)

def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


# Ruta principal de nuestra aplicacion


def logError(errores):
    file = open("./logMonitor.txt", "a")

    for i,j in errores.items():
        file.write(strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + " " + i + " " + j + os.linesep)
    file.close()
@app.route("/")
def main():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        # LLamada a las funciones que utilizamos
        # requestFiles()

        request_printer()
        request_job()
        #get_json_printer()
        #get_json_job()

        #print ("JSONIFY" + str(jsonify(get_json_job())))
        #print ("A PELO EL JSON: " + str(get_json_job()))
        nombres_ordenados = collections.OrderedDict(sorted(nombres.items()))
        datos_finales_job_ordenados = collections.OrderedDict(sorted(datosFinalesJob.items()))

        return Response(stream_template('index.html', datosFiles=datosFinalesFiles, datosPrinter=datosFinalesPrinter,
                               datosJob=datos_finales_job_ordenados,
                               fallos=errores, nombresMaquinas=nombres, nombresOrdenados=nombres_ordenados,
                               datosJsonJob=datosJsonJob, datosJsonPrinter=datosJsonPrinter))

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=False, host='0.0.0.0', port=5000)

# Dentro del servidor
# app.run(host='0.0.0.0',port=8050)
