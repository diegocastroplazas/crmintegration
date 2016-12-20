'''
CRMIntegration
author: Diego Castro
company: OpenBCO
copyright: 2016

'''

import urllib2
import json
import urllib
import requests
import MySQLdb
import sys
import datetime
import logging
from hashlib import md5

reload(sys)
sys.setdefaultencoding("utf-8")

logging.basicConfig(filename="middleware.log", level=logging.DEBUG, format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')

logging.debug("This is a debug message")
logging.info("Informational message")
logging.error("An error has happened!")


class CRMIntegration:

    #Constructor de la clase CRMIntegration
    #Se definen todas las variables

    def __init__ (self, urlBase):

        logging.info("Inicializando Middleware")


        self.url = urlBase + '/webservice.php'
        self.username = "desarrollo1"
        self.accessKey = "CoRTFco4EJyNUE9"

        #Configuracion de la base de datos del Middleware
        dbMiddlewareSettings = {

            'host': '192.168.33.21',
            'user': 'testcrm',
            'password': 'telconet894518',
            'db': 'middleware'
        }

        dbCRMSettings = {

            'host': '192.168.33.21',
            'user': 'testcrm',
            'password': 'telconet894518',
            'db': 'crmtn2'
        }

        self.dbCRMSettings = dbCRMSettings
        self.dbMiddlewareSettings = dbMiddlewareSettings

        self.equivalences = {

            "nit_real": 'siccode',
            "nombres": 'accountname',
            "tipo_identificacion": "cf_559",
            "telefono_1": 'phone',
            "fax": 'fax',
            "telefono_2": 'otherphone',
            "mail": 'email1',
            "vendedor": 'assigned_user_id',
            "direccion": 'bill_street',
            "y_ciudad": 'cf_708',
            "y_dpto": 'cf_707',
            "y_pais": 'cf_706',
            "tipo_persona": 'cf_558',
            "tipo_cliente": 'cf_562',
            "tipo_carga": 'cf_709',
            "actividad_comer": 'cf_565',
            "razon_comercial": 'cf_566',
            "sector": 'cf_568',
            "tipo_tercero": 'cf_569',
            "segmento": 'cf_570',
            "celular": 'cf_578',
            "contacto_1": 'cf_579'

        }



        self.prepareDBs()


    def login(self):

        args = {'operation': 'getchallenge', 'username': self.username}

        try:
            r = requests.get(self.url, params=args)
            print(r.url)
            response = json.loads(r.text.decode('utf-8'))

        except requests.exceptions.RequestException as e:
            print e
            logging.debug('Error al conectar con CRM: ' + str(e))
            self.createAlertInOpManager(e)
            sys.exit(1)


        if (str(response['success'])=='True'):

            print "Respuesta satisfactoria"
            token = response['result']['token']

            key = md5(token + self.accessKey)
            tokenizedAccessKey = key.hexdigest()

            args['accessKey'] = tokenizedAccessKey
            args['operation'] = 'login'


            data = urllib.urlencode(args)
            req = urllib2.Request(self.url, data)
            response = urllib2.urlopen(req)
            response = json.loads(response.read())
            print (str(response))

            if (str(response['success'])=='True'):
                print "Logueado"
                self.sessionArgs = response['result']
                print (str(self.sessionArgs))
            else:
                message = str(response["error"])
                self.createAlertInOpManager(message)
                sys.exit(1)

        else:
            print "No se tuvo respuesta"
            return False

    '''
    Conexion a las bases de datos.

    '''
    def prepareDBs(self):

        try:
            dbParamsC = self.dbCRMSettings
            dbC = MySQLdb.connect(dbParamsC['host'],dbParamsC['user'],dbParamsC['password'],dbParamsC['db'] )
        except (MySQLdb.Error, MySQLdb.Warning )as e:
            logging.error("Error al conectar con la base de datos: Error Obtenido: " + str(e))
            self.createAlertInOpManager(e)
            return False
        else:
            self.dbCRMConn = dbC
            logging.info("Conectado a CRM")

        try:
            dbParamsM = self.dbMiddlewareSettings
            dbM = MySQLdb.connect(dbParamsM['host'],dbParamsM['user'],dbParamsM['password'],dbParamsM['db'] )
        except (MySQLdb.Error, MySQLdb.Warning )as e:
            logging.error("Error al conectar con la base de datos: Error Obtenido: " + str(e))
            print (e)
            self.createAlertInOpManager(e)
            return False
        else:
            self.dbMiddlewareConn = dbM
            logging.info("Conectado a Middleware")


    #Crea una cuenta
    def createAccount(self, account):

        logging.info('Cargue de cuenta iniciado para NIT: ' + str(account["nit_real"]))
        self.messageExecution = []
        accountData = {}
        i=1
        for k, v in self.equivalences.iteritems():
            if (account.has_key(k)):
                stringd = str(account[k])
                stringproc = stringd.decode('utf-8', errors='ignore').encode('utf-8')
                accountData[str(v)] = stringproc
            else:
                accountData[str(v)] = 'No existe'
                logging.debug('El parametro: ' + str(v) + 'no existe')
            i = i+1

        #Si no tiene un vendedor asignado
        if (account['vendedor'] == ''):
            accountData['assigned_user_id'] = self.sessionArgs['userId']
            logging.debug('No se encontro vendedor asignado para la cuenta ' + str(account['nit_real']))
        else:
            accountData['assigned_user_id'] = '19x' + self.getAssignedUserID(account['vendedor'])


        accountData['cf_706'] = self.getCountry(account['y_pais'])
        accountData['cf_707'] = self.getState(account['y_dpto'])
        accountData['cf_708'] = self.getCity(account['y_dpto'],account['y_ciudad'])

        accountData['cf_576'] = "Activo"
        accountData['cf_685'] = "Activo"

        serializedAccount = json.dumps(accountData)
        print (serializedAccount)

        moduleName = 'Accounts'

        parames = {
            "operation": "create",
            "sessionName": self.sessionArgs['sessionName'],
            "element": serializedAccount,
            "elementType": moduleName
        }

        data = urllib.urlencode(parames)
        print (data)
        req = urllib2.Request(self.url, data)
        response = urllib2.urlopen(req)
        #response = json.loads(response.read())
        result = response.read()
        print (result)
        logging.info("Resultado obtenido al crear la cuenta: " + str(result))

        self.insertLog(accountData,result)

    def obtainAccountsFromSource(self):

        cursor = self.dbMiddlewareConn.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM accounts")
            result_set = cursor.fetchall()
            print (str(result_set))
            return result_set
        except:
            print "Unable to fecth data"

    def isSyncronized(self, nit):

        print ("Entro a la funcion isSyncronized")

        cursor = self.dbCRMConn.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT siccode FROM vtiger_account WHERE siccode = '%s'" % (nit)
        cursor.execute(query)
        result  = cursor.fetchone()

        if result:
            print str(result['siccode'])
            print "EL NIT YA ESTA EN LA BASE DE DATOS"
            return False
        else:
            print "EL NIT NO ESTA EN LA BASE DE DATOS"
            return True


    '''
    CRMIntegration.getAssignedUserID() Devuelve el ID del vendedor o usuario asignado. Si el vendedor no existe, retorna un '1', el cual corresponde al ID de Administrador.

    @param self tipo CRMIntegration: Es la instancia de la clase.
    @param cc string, corresponde a la cedula o nit del vendedor.
    '''
    def getAssignedUserID(self, cc):

        cursor = self.dbCRMConn.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT id FROM vtiger_users WHERE description = '%s'" % (cc)
        cursor.execute(query)
        result  = cursor.fetchone()
        print ("EL ID DEL VENDEDOR ES: ")
        if result:
            val = str(result['id'])
            self.messageExecution.append('--El vendedor existe--')
        else:
            val = '1'
            self.messageExecution.append('-- El vendedor no existe --')
        return val

    def getCountry(self, cod):

        cursor = self.dbMiddlewareConn.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT paiscrm FROM pais WHERE codpais = '%s'" % (cod)
        cursor.execute(query)
        result  = cursor.fetchone()

        if result:
            val = str(result['paiscrm'])
            self.messageExecution.append('--El pais existe--')
        else:
            val = '1'
            self.messageExecution.append('--El pais no existe--')
        return val



    def getState(self,stateCode):

        cursor = self.dbMiddlewareConn.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT departamentocrm FROM departamento WHERE coddepartamento='%s'" % (stateCode)

        cursor.execute(query)
        result  = cursor.fetchone()

        if result:
            val = str(result['departamentocrm'])
            self.messageExecution.append('--El dpto existe--')
        else:
            val = '1'
            self.messageExecution.append('--El dpto no existe--')
        return val

    def getCity(self, stateCode, cityCode):
        print "DPTO: "
        print stateCode
        print "CIUDAD: "
        print cityCode

        city = str(stateCode) + str(cityCode)
        print city

        cursor = self.dbMiddlewareConn.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT ciudadcrm FROM ciudad WHERE codciudad = '%s'" % (city)

        cursor.execute(query)
        result  = cursor.fetchone()

        if result:
            val = str(result['ciudadcrm'])
            self.messageExecution.append('-- La ciudad existe--')
        else:
            val = '1'
            self.messageExecution.append('-- La ciudad existe--')
        return val


    def insertLog(self, accountParams, status):

        myString = " ".join(self.messageExecution)
        createdTime = datetime.datetime.now()
        print (createdTime)
        statusLoad = ''
        print ("Vooy a registrar en Log")
        print (str(accountParams['siccode']))
        status = json.loads(status)
        print (status["success"])

        nitCuenta = str(accountParams['siccode'])
        nitCuenta = int(nitCuenta)

        if (status["success"]):
            print ("Resultado satisfactorio")
            statusLoad = 'Success'
        else:
            statusLoad = 'Failed'

        message = str(status["result"])

        cursor = self.dbMiddlewareConn.cursor()

        sql = "INSERT INTO transaction(nit, \
               status, annotation, empresa, createdtime) \
               VALUES ('%d', '%s', '%s', '%s', '%s')" % \
               (nitCuenta, statusLoad, myString, 'TECNODIESEL', createdTime)


        cursor.execute(sql)
        self.dbMiddlewareConn.commit()

    def createAlertInOpManager(self, text):

        print(text)

        API_KEY = '2ceef3cc53cf3528add17739eb1ff0a9'
        url_base = 'http://vps81053.vps.ovh.ca:8060'
        URL = url_base + '/api/json/events/addEvent'

        alertParameters = {

            'apiKey': API_KEY,
            'source': 'SRV_TECNODIESEL',
            'severity': '1',
            'message': text,
            'alarmCode': 'Threshold-DOWN',
            'entity': 'SRV_TECNODIESEL'
        }

        r = requests.post(URL, params=alertParameters)
    	message = json.loads(r.text.decode('utf-8'))
        print (str(message))

    def endProcess(self):

        self.dbCRMConn.close()
        self.dbMiddlewareConn.close()



def main():

    URL = 'http://192.168.33.21/crmtn2'
    conn = CRMIntegration(URL)



    login = conn.login()
    accounts = conn.obtainAccountsFromSource()
    for account in accounts:
        if conn.isSyncronized(account["nit_real"]):
            print "No hago nada"
        else:
            print "Debo sincronizar"
            conn.createAccount(account)





if __name__ == '__main__':
	main()
