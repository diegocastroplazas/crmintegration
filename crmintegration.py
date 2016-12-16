import urllib2
import json
import urllib
import requests
import MySQLdb
import sys
from hashlib import md5

reload(sys)
sys.setdefaultencoding("utf-8")

class CRMIntegration:

    #Constructor de la clase CRMIntegration
    #Se definen todas las variables

    def __init__ (self, urlBase):

        self.url = urlBase + '/webservice.php'
        self.username = "desarrollo1"
        self.accessKey = "CoRTFco4EJyNUE9"

        dbSettings = {

            'host': '192.168.33.21',
            'user': 'testcrm',
            'password': 'telconet894518',
            'db': 'middleware'
        }

        self.dbCRM = dbSettings

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

    #Establece conexion con el CRM
    #Retorna los parametros de login.

    def login(self):

        args = {'operation': 'getchallenge', 'username': self.username}

        r = requests.get(self.url, params=args)
        print(r.url)
        response = json.loads(r.text.decode('utf-8'))
        print ("Respuesta")
        print (str(response))

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
                print "No se pudo completar el proceso de Logueo"

        else:
            print "No se tuvo respuesta"
            return False

    #Crea una cuenta
    def createAccount(self, account):

        accountData = {}
        #print(str(account))
        i=1
        for k, v in self.equivalences.iteritems():
            if (account.has_key(k)):
                stringd = str(account[k])
                stringproc = stringd.decode('utf-8', errors='ignore').encode('utf-8')
                accountData[str(v)] = stringproc
            else:
                accountData[str(v)] = 'No existe'
                print "El parametro no existe"
            i = i+1


        print ("EL NIT DEL VENDEDOR ES: ")
        print (str(account['vendedor']))
        if (account['vendedor'] == ''):
            accountData['assigned_user_id'] = self.sessionArgs['userId']
        else:
            accountData['assigned_user_id'] = '19x' + self.getAssignedUserID(account['vendedor'])
            #accountData['assigned_user_id'] = self.sessionArgs['userId']
        #accountData[self.equivalences[]]


        print ("accountData: ")
        print (str(accountData))

        serializedAccount = json.dumps(accountData)
        #serializedAccount = json.dumps(accountData)
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
        print (str(response.read()))



    def listTypes(self):

        parameters =  {'operation': 'listtypes', 'sessionName': self.sessionArgs['sessionName']}
        r = requests.get(self.url, params=parameters)
        print(r.url)
        response = json.loads(r.text.decode('utf-8'))
        print (str(response))


    #Funcion que ejecuta un query en la base de datos
    def obtainAccountsFromSource(self):

        print (str(self.dbCRM))

        db = MySQLdb.connect(str(self.dbCRM['host']),str(self.dbCRM['user']),str(self.dbCRM['password']),str(self.dbCRM['db']))

        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM accounts")
            result_set = cursor.fetchall()
            return result_set
        except:
            print "Unable to fecth data"

    def isSyncronized(self, nit):

        db = MySQLdb.connect(str(self.dbCRM['host']),str(self.dbCRM['user']),str(self.dbCRM['password']),str(self.dbCRM['db']))
        cursor = db.cursor()


        query = "SELECT nit_real FROM accounts WHERE nit_real = '%s'" % (nit)
        cursor.execute(query)
        result  = cursor.fetchone()
        if (str(result) == nit):
            #print "El NIT existe"
            return True
        else:
            #print "No existe"
            return False

    def getAssignedUserID(self, cc):

        db = MySQLdb.connect(str(self.dbCRM['host']),str(self.dbCRM['user']),str(self.dbCRM['password']),'crmtn2')
        #cursor = db.cursor()
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT id FROM vtiger_users WHERE description = '%s'" % (cc)
        cursor.execute(query)
        result  = cursor.fetchone()
        print ("EL ID DEL VENDEDOR ES: ")
        print (result)
        if result:
            val = str(result['id'])
        else:
            val = '1'
        return val


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
