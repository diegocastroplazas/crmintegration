import sys
# Absolute/Relative path of vtwsclib/Vtiger folder
from WSClient import *
# Create Vtiger Webservice client
client = Vtiger_WSClient('http://v3.telco.net.co/crmtn2')
login = client.doLogin('admin', ' KnO5G849ptdvTqW')
if login:
    print 'Login Successful'
else:
    print 'Login Failed!'
