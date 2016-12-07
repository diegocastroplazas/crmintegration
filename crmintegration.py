import urllib2
import json
import urllib
import requests
import pymysql.cursors
from hashlib import md5

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
            'db': 'crmtn2'
        }

        self.dbCRM = dbSettings

    #Establece conexion con el CRM
    #Retorna los parametros de login.

    def login(self):

        args = {'operation': 'getchallenge', 'username': self.username}

        r = requests.get(self.url, params=args)
        print(r.url)
        response = json.loads(r.text.decode('utf-8'))
        print (str(response))

        #TO-DO validar que la respuesta sea correcta
        token = response['result']['token']
        print (str(token))

        #Login...

        key = md5(token + self.accessKey)
        tokenizedAccessKey = key.hexdigest()
        args['accessKey'] = tokenizedAccessKey
        args['operation'] = 'login'
        data = urllib.urlencode(args)
        req = urllib2.Request(self.url, data)
        response = urllib2.urlopen(req)
        response = json.loads(response.read())

        # set the sessionName
        args['sessionName'] = response['result']['sessionName']
        args['userId'] = response['result']['userId']
        print (str(args))
        self.sessionArgs = args
        return args

    #Crea una cuenta
    def createAccount(self):

        idUser = self.sessionArgs['userId']
        contactData = {'lastname': 'Prueba', 'assigned_user_id': idUser}
        serializedContact = json.dumps(contactData)
        print (serializedContact)
        moduleName = 'Contacts'
        print (self.sessionArgs['sessionName'])

        parames = {
            "operation": "create",
            "sessionName": self.sessionArgs['sessionName'],
            "element": serializedContact,
            "elementType": moduleName
        }

        data = urllib.urlencode(parames)
        print (data)
        req = urllib2.Request(self.url, data)
        response = urllib2.urlopen(req)
        response = json.loads(response.read())


        #TO_DO: MANEJAR ERROR DE OOPERATION FAILED
        print(str(response))

    def listTypes(self):

        parameters =  {'operation': 'listtypes', 'sessionName': self.sessionArgs['sessionName']}
        r = requests.get(self.url, params=parameters)
        print(r.url)
        response = json.loads(r.text.decode('utf-8'))
        print (str(response))

    def describeObject(self, objName):

        parameters =  {'operation': 'describe', 'sessionName': self.sessionArgs['sessionName'], 'elementType': objName}
        r = requests.get(self.url, params=parameters)
        print(r.url)
        response = json.loads(r.text.decode('utf-8'))
        print (str(response))


    #Funcion que ejecuta un query en la base de datos
    def executeQuery(self, target):

        query = "SELECT `id`, `password` FROM `users` WHERE `email`=%s"

        if target == 'CRM':
            connParameters = self.dbCRM
            print str(connParameters)

        connection = pymysql.connect(host=connParameters['host'],
                             user=connParameters['user'],
                             password=connParameters['password'],
                             db=connParameters['db'],
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                print (result)
        finally:
            connection.close()


def main():

    URL = 'http://v3.telco.net.co/crmtn2'
    conn = CRMIntegration(URL)
    parameters = conn.login()
    conn.createAccount()
    conn.executeQuery('CRM')
    #conn.listTypes()conn.describeObject('Accounts')


if __name__ == '__main__':
	main()
