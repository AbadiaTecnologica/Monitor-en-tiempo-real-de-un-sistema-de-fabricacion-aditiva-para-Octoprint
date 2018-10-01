#!/usr/bin/python2.7


'''
__author__ = "David Zotes"
__license__ = "GPL3.0"
__version__ = "1.0.0"
__email__ = "zotesgonzalez@gmail.com"
'''

from flask import Flask,render_template
from flask import jsonify
from flask import request
from datetime import datetime,timedelta
import json as simplejson
import requests
import threading



app = Flask(__name__)


		
#Direccion sobre la que corre el Octoprint dentro del servidor.
#host = "http://127.0.0.1"
#Direccion sobre la que corre el Octoprint.
host = "http://192.168.1.200"

#Archivo files API Octoprint.
files = "files"

#Archivo printer API Octoprint.
printer = "printer"

#Archivo job API Octoprint (para monitorizar las impresiones en curso).
job = "job"

#Direccion de la API para conectar o desconectar las impresoras mediante una peticion POST
conn="connection"


#Lista en las que se guardan los datos utiles que vamos a mostrar.
valoresFiles = list()
valoresPrinter = dict()
valoresJob=dict()

#Diccicionarios con clave el id de la maquina y valor los datos de cada maquina.
datosFinalesFiles = dict()
datosFinalesPrinter = dict()
datosFinalesJob = dict()

#Un diccionario para guardar los errores que se hayan podido producir en las peticiones a la API.
errores=dict()


#Array con los identificadores de las maquinas y las direcciones con el proxy para poner los enlaces en el index
nombres=dict()



 #Array de las maquinas con el puerto el id de la maquina y el token de la API
maquinas = [["5001", "maq1", "X-Api-Key"],
	        ["5002", "maq2", "X-Api-Key"],
	        ["5003", "maq3", "X-Api-Key"],
	        ["5004", "maq4", "X-Api-Key"],
	        ["5005", "maq5", "X-Api-Key"],
	        ["5006", "maq6", "X-Api-Key"],
	        ["5007", "maq7", "X-Api-Key"]]

#Array con los identificadores de las maquinas y las direcciones con el proxy para poner los enlaces en el index
nombres["maq1"]={"Nombre":"Impresora1", "direccion":str("./3dp1")}
nombres["maq2"]={"Nombre":"Impresora2", "direccion":str("./3dp2")}
nombres["maq3"]={"Nombre":"Impresora3", "direccion":str("./3dp3")}
nombres["maq4"]={"Nombre":"Impresora4", "direccion":str("./3dp4")}
nombres["maq5"]={"Nombre":"Impresora5", "direccion":str("./3dp5")}
nombres["maq6"]={"Nombre":"Impresora6", "direccion":str("./3dp6")}
nombres["maq7"]={"Nombre":"Impresora7", "direccion":str("./3dp7")}

#Funcion que devuelve los datos de las impresiones que hayan finalizado de cada maquina. (Actualmente no esta funcionando).			
# def pideDatosFiles(datos, idmaquina):


# 	valoresFiles = list()

# 	for i in range(0, len(datos)):

# 		valoresFiles.append("Fecha: " + datetime.fromtimestamp(datos["files"][i]["date"]).strftime(' %I:%M %p %b. %d, %y'))
# 		valoresFiles.append("Nombre: " + datos["files"][i]["display"])

# 		tiempo=datos["files"][i]["gcodeAnalysis"]["estimatedPrintTime"]
# 		m, s = divmod(tiempo,60)
# 		h, m = divmod(m, 60)
# 		valoresFiles.append("Tiempo estimado impresion: " + "%d:%02d:%02d" % (h, m, s))
# 		valoresFiles.append("____________________________________________")
		

# 	return valoresFiles


#Funcion que devuelve los datos de impresora (temperaturas de cama y extrusor).
def pideDatosPrinter(datos):
	
	#Diccionario temporal en el que iremos guardando nuestros valores utiles.
	valoresPrinter=dict()

	#Pausa
	valoresPrinter["Pausa"]=str(datos["state"]["flags"]["paused"])

	#Imprimiendo
	valoresPrinter["Imprimiendo"]= str(datos["state"]["flags"]["printing"])

	#Lista
	valoresPrinter["Lista"] = str(datos["state"]["flags"]["ready"])

	#Estado Impresora (conectada o no)
	valoresPrinter["Estado"]=str(datos["state"]["text"])

	#Comprobamos que la impresora este conectada mediante las lecturas de temperatura
	if len(datos["temperature"]) == 0:
		print("Conflicto con la API en Printer (impresora desconectada)")
	else:
		#Temperatura actual de la cama
		valoresPrinter["TempCamaActual"] = str(datos["temperature"]["bed"]["actual"])

		#Temperatura fijada de la cama
		valoresPrinter["TempCamaFijada"] = str(datos["temperature"]["bed"]["target"])

		#Temperatura actual del extrusor
		valoresPrinter["TempHottendActual"] = str(datos["temperature"]["tool0"]["actual"])

		#Temperatura fijada de extrusor
		valoresPrinter["TempHottendFijada"] = str(datos["temperature"]["tool0"]["target"])

	#Devolvemos el diccionario con los datos de cada maquina.
	return valoresPrinter


#Funcion que devuelve los datos de la impresion en curso (Timepo, Timeleft, Porcentaje completado...).
def pideDatosJob(datos):
	
	#Diccionario temporal en el que guardaremos nuestros datos utiles.
	valoresJob=dict()
	
	#Comprabamos que el tiempo estimado de impresion no es None, y entonces cambiamos el formato a uno legible.
	if datos["job"]["estimatedPrintTime"] is None:
		valoresJob["TiempoEstimadoImpresion"]=str(datos["job"]["estimatedPrintTime"])
	else:
		tiempo=datos["job"]["estimatedPrintTime"]
		m, s = divmod(tiempo,60)
		h, m = divmod(m, 60)
		#Hacemos la conversion y lo guardamos en nuestro diccionario en horas, minutos y segundos.
		valoresJob["TiempoEstimadoImpresion"]="%d:%02d:%02d" % (h, m, s)

	#Nombre del archivo que esta imprimiendo
	valoresJob["Nombre"]=str(datos["job"]["file"]["name"])

	#Tiempo que duro la ultima impresion y hacemos la misma conversion de antes para que los datos sean legibles.
	if datos["job"]["lastPrintTime"] is None:
		valoresJob["TiempoUltimaImpresion"]=str(datos["job"]["lastPrintTime"])
	else:
		tiempo=datos["job"]["lastPrintTime"]
		m, s = divmod(tiempo,60)
		h, m = divmod(m, 60)
		valoresJob["TiempoUltimaImpresion"]= "%d:%02d:%02d" % (h, m, s)

	#Porcetaje de impresion que se ha completado
	valoresJob["Porcentaje"]=str(datos["progress"]["completion"])


	#Tiempo que lleva de impresion (pieza actual). Hacemos la misma coversion anterior.
	if datos["progress"]["printTime"] is None:
		valoresJob["TiempoImpresion"]=str(datos["progress"]["printTime"])
	else:
		tiempo=datos["progress"]["printTime"]
		m, s = divmod(tiempo,60)
		h, m = divmod(m, 60)
		valoresJob["TiempoImpresion"]="%d:%02d:%02d" % (h, m, s)


	#Tiempo que le queda a la impresion actual. Hacemos la misma coversion anterior.
	if datos["progress"]["printTimeLeft"] is None:
		valoresJob["TiempoRestante"]=str(datos["progress"]["printTimeLeft"])
	else:
		tiempo=datos["progress"]["printTimeLeft"]
		m, s = divmod(tiempo,60)
		h, m = divmod(m, 60)
		valoresJob["TiempoRestante"]= "%d:%02d:%02d" % (h, m, s)
	#Estado de la impresora
	valoresJob["Estado"]= str(datos["state"])

	
	#Devolvemos el diccionario con los datos de cada maquina.
	return valoresJob


#Funcion que hace las peticiones a la API de cada maquina para obtener el JSON files
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

#Funcion que hace las peticiones a la API de cada maquina para obtener el JSON printer
def requestPrinter():
	for i in range(0, len(maquinas)):
		maquina = maquinas[i]
		urlstring = str(host + ":" + maquina[0] + "/api/"+ printer + "?apikey=" + maquina[2]) #Direccion con la que haremos la peticion GET
		try:
			resp = requests.get(url=urlstring)
			
			#Control de errores (se pueden comentar)
			#print ("resp: "+str(resp))
			#print("status code: " + str(resp.status_code))
			#print("tipo status code: " + str(type(resp.status_code)))
			#print("tipo de resp: " + str(type(resp)))
			#print ("datos resp = " + str(resp.content))
			#print ("datos resp tipo = " + str(type(resp.content)))

			#Parseamos la respuesta para que sea JSON.
			data = resp.json()
		except Exception as e:
			datosJson =list()
			strfallo = "Error en i= %d: %s"
			print (strfallo %(i, str(e)))
			print("resp del if: " + str(resp))

			#Controlamos los posibles errores que nos pueden dar y los capturamos para que la aplicacion siga en funcionamiento,
			#a pesar de que una maquina pueda fallar.
			if resp == None:
				errores[maquina[1]]="El servicio de Octoprint no esta operativo"
			else:
				if resp.status_code == 204:
					errores[maquina[1]]="La respuesta de la API no tiene contenido"
				elif resp.status_code == 409:
					#errores[maquina[1]]="La impresora no esta operativa"
					print("La impresora no esta operativa (409)")
				elif resp.status_code == 404:
					errores[maquina[1]]="No hay comunicacion por parte del servidor"
				elif resp.status_code == 200:
					print("La respuesta es correcta")
					#Seguramente se tendra que comentar, se usa a modo debug
					#datosJson.append(str(data.content()))
				elif resp.status_code == 500:
					errores[maquina[1]]="Internal server error"
	
		else: #Else del try
			datosFinalesPrinter[maquina[1]] = pideDatosPrinter(data)


#Funcion que hace las peticiones a la API de cada maquina para obtener el JSON job
def requestJob():
	for i in range(0, len(maquinas)):
		maquina = maquinas[i]
		urlstring = str(host + ":" + maquina[0] + "/api/" + job + "?apikey=" + maquina[2]) #Direccion con la que haremos la peticion GET
		try:
			resp = requests.get(url=urlstring)
			#Parseamos la respuesta para que sea JSON.
			data = resp.json()
		except Exception as e:

			if resp == None:
				errores[maquina[1]]="El servicio de Octoprint no esta operativo"
			else:

				datosJson =list()
				strfallo = "Error en i= %d: %s"
				print (strfallo %(i, str(e)))
				print("resp del if: " + str(resp))

				if resp.status_code == 204:
					errores[maquina[1]]="La respuesta de la API no tiene contenido"
				elif resp.status_code == 409:
					#errores[maquina[1]]="La impresora no esta operativa"
					print("La impresora no esta operativa (409)")
				elif resp.status_code == 404:
					errores[maquina[1]]="No hay comunicacion por parte del servidor"
				elif resp.status_code == 200:
					print("La respuesta es correcta")
					#Seguramente se tendra que comentar, se usa a modo debug
					#datosJson.append(str(data.content()))
				#else:
					#errores[maquina[1]]= "Hay algun error desconocido"
		else: #Else del try
			datosFinalesJob[maquina[1]] = pideDatosJob(data)	

#Ruta para llamar a la funcion que conecta las maquinas
@app.route("/conectar")

#Funcion que conecta las maquinas.
def conectar():

	#Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
	id_maq=request.args.get("maq", default =-1, type = int)
	#print("id maquina: "+ str(id_maq))

	#Sino le pasas nada por parametro, pondra por defecto -1 y significa que hay que conectar todas las maquinas.
	if id_maq==-1:

		print("borrar todas")
		#Sirve para conectar todas las maquinas, pero actualmente no esta en funcionamiento. 
		#Tan solo seria repetir el bucle inicial de las funciones anteriores.
		#for i in range(0, len(maquinas)):
		if None:
			print("None")
			maquina = maquinas[i]
			print("Maquina: " + maquina)
			headers = {'Content-Type': 'application/json','X-Api-Key': maquina[2]}
			data= '{"command": "connect"}'
			urlConectar= str(host + ":" + maquina[0] + "/api/" + conn)
			peticion=requests.post(urlConectar,data=data,headers=headers)

			#Para pruebas
			#print("request: " + str(peticion))
			#print("status code: " + str(peticion.status_code))
			#print("tipo status code: " + str(type(peticion.status_code)))
			#print("tipo de request: " + str(type(peticion)))
			#print("datos request = " + str(peticion.content))
			#print("datos request tipo = " + str(type(peticion.content)))

	#Conectar la maquina que le hemos dicho especificamente.
	else:
		maquina= maquinas[id_maq-1]
		print("Entra en el else:")
		headers = {'Content-Type': 'application/json','X-Api-Key': maquina[2]}
		data= '{"command": "connect"}'
		urlConectar= str(host + ":" + maquina[0] + "/api/" + conn)
		peticion=requests.post(urlConectar,data=data,headers=headers)

		#Para pruebas
		# print("request else: " + str(peticion))
		# print("status code else: " + str(peticion.status_code))
		# print("tipo status code else: " + str(type(peticion.status_code)))
		# print("tipo de request else: " + str(type(peticion)))
		# print("datos request else = " + str(peticion.content))
		# print("datos request tipo else = " + str(type(peticion.content)))

		#Despues de conectar un maquina devolvemos el main para que vuelva a cargar la pagina principal con todos los datos.
	return main()
	

	


#Ruta para llamar a la funcion que desconecta las maquinas
@app.route("/desconectar")

#Funcion que desconecta las maquinas.
def desconectar():
	
	#Extrae el id maquina de los argumentos de la URL y lo guarda en id_maq.
	id_maq=request.args.get("maq", default =-1, type = int)
	#print("id maquina: " +str (id_maq))

	#Sino le pasas nada por parametro, pondra por defecto -1 y significa que hay que desconectar todas las maquinas.
	if id_maq==-1:

		print("borrar todas")
		#Sirve para desconectar todas las maquinas, pero actualmente no esta en funcionamiento. 
		#Tan solo seria repetir el bucle inicial de las funciones anteriores.
		#for i in range(0, len(maquinas)):
		if None:
			print("None")
			maquina = maquinas[i]
			print("Maquina: " + maquina)
			headers = {'Content-Type': 'application/json','X-Api-Key': maquina[2]}
			data = '{"command": "disconnect"}'
			urlConectar= str(host + ":" + maquina[0] + "/api/" + conn)
			peticion=requests.post(urlConectar,data=data,headers=headers)

			# print("request: " + str(peticion))
			# print("status code: " + str(peticion.status_code))
			# print("tipo status code: " + str(type(peticion.status_code)))
			# print("tipo de request: " + str(type(peticion)))
			# print("datos request = " + str(peticion.content))
			# print("datos request tipo = " + str(type(peticion.content)))

		
	else:
		maquina= maquinas[id_maq-1]
		print("Entra en el else:")
		headers = {'Content-Type': 'application/json','X-Api-Key': maquina[2]}
		data= '{"command": "disconnect"}'
		urlConectar= str(host + ":" + maquina[0] + "/api/" + conn)
		peticion=requests.post(urlConectar,data=data,headers=headers)
	
		# print("request else: " + str(peticion))
		# print("status code else: " + str(peticion.status_code))
		# print("tipo status code else: " + str(type(peticion.status_code)))
		# print("tipo de request else: " + str(type(peticion)))
		# print("datos request else = " + str(peticion.content))
		# print("datos request tipo else = " + str(type(peticion.content)))

		#Despues de conectar un maquina devolvemos el main para que vuelva a cargar la pagina principal con todos los datos.
	return main()

	
#Ruta principal de nuestra aplicacion
@app.route("/")

def main():

	#LLamada a las funciones que utilizamos
	#requestFiles()
	requestPrinter()
	requestJob()

	
	#parsed_json= jsonify(json_string)

	#parsed_json = json.loads(json_string)
	#data = []
	#funcionDatosJson(data)

	return render_template('index.html', datosFiles = datosFinalesFiles, datosPrinter = datosFinalesPrinter,datosJob=datosFinalesJob,
	 fallos = errores, nombresMaquinas=nombres)

if __name__=="__main__":
	app.run(host='0.0.0.0')
#Dentro del servidor
	#app.run(host='0.0.0.0',port=8050)
