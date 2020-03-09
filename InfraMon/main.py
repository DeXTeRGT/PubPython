import hashlib
import sqlalchemy
import logging
import sys
import threading
import time
import numpy as np
import random
import mplwidget

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox
from resource import uiresources
from configparser import ConfigParser
from sqlalchemy import create_engine
from pathlib import Path

from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)

config_file='config/config.ini'
config_parse = ConfigParser()

if Path(config_file).is_file():
    config_parse.read('config/config.ini')
else:
    sys.exit(1)

logger=logging.getLogger('[InfraMon]')
logger.setLevel(logging.DEBUG)

err_log=logging.FileHandler('log/' +  config_parse.get('GENERAL','err_log'))
app_log=logging.FileHandler('log/' +  config_parse.get('GENERAL','app_log'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

err_log.setLevel(logging.ERROR)
app_log.setLevel(logging.DEBUG)

err_log.setFormatter(formatter)
app_log.setFormatter(formatter)

logger.addHandler(err_log)
logger.addHandler(app_log)

db_name='database/' + config_parse.get('GENERAL','db_name')

if Path(db_name).is_file():
    logger.info('Database file is available')
else:
    sys.exit(1)

try:
    logger.info('Connecting to InfraMon database')
    engine=create_engine('sqlite:///'+db_name)
    logger.debug('Connected to database - sqlite:///' + db_name)
except Exception as ErrorHandle:
    logger.critical(str(ErrorHandle))
    sys.exit(1)    

class UpdateThread(QtCore.QThread):
    get_lbl_sql = 'select * from instant'
    get_lbl_res=engine.execute(get_lbl_sql)
    for r_ in get_lbl_res:
        exec(r_[1]+'=QtCore.pyqtSignal(str)')
        exec(r_[1]+'_css=QtCore.pyqtSignal(str)')
    update_status_bar=QtCore.pyqtSignal(str)

    def __init__(self,  parent=None): #init class - as far as i know is not mandatory ... but ok
        QtCore.QThread.__init__(self, parent)
        self.running = False

    def run(self):   #define a method that would emit a str signal from time to time (3 sec apart)
        self.running = True
        #self.str_signal.emit('<font color=green><b>[INFO]</b></font>GUI update thread id: ' + str(int(QtCore.QThread.currentThreadId())))
        while self.running:
            #self.update_status_bar.emit('Reading from database')
            get_lbl_sql = 'select * from instant'
            get_lbl_res=engine.execute(get_lbl_sql)
            for r_ in get_lbl_res:
                exec('self.' + r_[1] + '.emit(\'' + str(r_[2]) + '\')')
                if r_[3]==0 and r_[4]==0 and r_[5]==0:
                    exec('self.' + r_[1] + '_css.emit(\'background-color: yellowgreen; border-radius:10px; color: black\')')
                if r_[2]>r_[4] and r_[4]!=0:
                    exec('self.' + r_[1] + '_css.emit(\'background-color: red; border-radius:10px; color: black\')')
                if r_[2]<r_[3] and r_[3]!=0:
                    exec('self.' + r_[1] + '_css.emit(\'background-color: peru; border-radius:10px; color: black\')')
                if r_[2]>r_[3] and r_[2]<r_[4]:
                    exec('self.' + r_[1] + '_css.emit(\'background-color: green; border-radius:10px; color: black;\')')                
            time.sleep(float(config_parse.get('GENERAL','refresh')))
            #self.update_status_bar.emit('Done from database')
            time.sleep(float(config_parse.get('GENERAL','refresh')))
    def stop(self):
        self.str_signal.emit('Background thread will be terminated after its outstanding work will be done')
        self.running=False


class Login(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Login, self).__init__(parent)
        uic.loadUi('ui/login.ui', self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.l_login.clicked.connect(self.handleLogin)
        self.l_cancel.clicked.connect(self.cancelLogin)

    def cancelLogin(self):
        sys.exit(0)

    def handleLogin(self):
        
        user_sql='select * from users where u_name="' + self.l_uname.text() + '" and u_pass="' + str(hashlib.sha256(self.l_pass.text().encode('utf-8')).hexdigest()) + '"'
        get_user=engine.execute(user_sql)
        auth_record=get_user.fetchone()
        if auth_record is None:
            QtWidgets.QMessageBox.critical(self, 'Login Error', 'Login denied!\nBad user or password!\nEvent had been logged!')
        else:
            if auth_record['is_active']!=1:
                QtWidgets.QMessageBox.information(self, 'Login Error', 'Username is not active\nEvent had been logged!')
            else:
                last_login_sql='update users set last_login=datetime(\'now\') where u_name="' + self.l_uname.text() + '"'
                engine.execute(last_login_sql)

                Window.logged_user=self.l_uname.text()
                
                if auth_record['is_admin']==1:
                    self.accept()
                    return 1

                if auth_record['is_editor']==1:
                    self.accept()
                    return 2
                    
                if auth_record['is_viewer']==1:
                    self.accept()
                    return 3


class EditUser(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super(EditUser, self).__init__(parent)
        uic.loadUi('ui/usermanagement.ui', self)
        #self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        get_avialable_users='select * from users'
        get_result_users=engine.execute(get_avialable_users)
        self.e_uname.addItem('')
        for r_ in get_result_users:
            self.e_uname.addItem(r_[1])
            #print(r_[1])
        self.e_uname.currentTextChanged.connect(self.LoadUserDetails)
        self.e_close.clicked.connect(self.CloseWindow)
        self.e_delete.clicked.connect(self.DeleteUser)
        #self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

    def CloseWindow(self):
        self.close()

    def DeleteUser(self):
        MsgBox= QMessageBox()
        getReply = MsgBox.question (self,'Delete user', 'Delete user ' + self.e_uname.currentText(), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if getReply == QMessageBox.Yes:
            user_delete_sql='delete from users where u_name="' + self.e_uname.currentText() + '"'
            engine.execute(user_delete_sql)
            
            insert_audit_sql='insert into audit (e_type, e_text, date,operator) values ("[USER DEL]","User deleted: ' + self.e_uname.currentText() + '",datetime(\'now\'),"' + Window.logged_user + '")'
            engine.execute(insert_audit_sql)
            
            self.e_uname.clear()
            get_avialable_users='select * from users'
            get_result_users=engine.execute(get_avialable_users)
            self.e_uname.addItem('')
            for r_ in get_result_users:
                self.e_uname.addItem(r_[1])

    def LoadUserDetails(self):
        print(self.e_uname.currentText())
        user_details_sql='select * from users where u_name="' + self.e_uname.currentText() + '"'
        get_user_details = engine.execute(user_details_sql)
        details = get_user_details.fetchone()

        if details is not None:
            self.is_active.setChecked(details[3])
            self.is_admin.setChecked(details[4])
            self.is_editor.setChecked(details[5])
            self.is_viewer.setChecked(details[6])
            if details[7] is not None:
                self.last_login.setText('Last login was on: ' + details[7])
            else:
                self.last_login.setText('No last login information')

class AddUser(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super(AddUser, self).__init__(parent)
        uic.loadUi('ui/adduser.ui', self)
      
        role=['Administrator', 'Editor', 'Viewer']
        is_active=['Inactive', 'Active']
        self.a_role.addItems(role)
        self.a_isactive.addItems(is_active)

        self.cancel_user.clicked.connect(self.CloseWindow)
        self.add_user.clicked.connect(self.AddNewUser)
        #self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        #self.show()

    def CloseWindow(self):
        self.close()

    def AddNewUser(self):
        MsgBox= QMessageBox()
        
        user_name=str(self.a_uname.text())
        user_pass=str(hashlib.sha256(self.a_password.text().encode('utf-8')).hexdigest())
        user_role=int(self.a_role.currentIndex())+1
        user_isactive=int(self.a_isactive.currentIndex())

        print(user_name)
        print(user_pass)
        print(user_role)
        print(user_isactive)

        if self.a_uname.text()=='' or self.a_password.text()=='':
            MsgBox.critical(self,'Error creating user', 'Username or password cannot be blank!')
        else:
            user_sql='select * from users where u_name="' + self.a_uname.text() +'"'
            add_user_sql='insert into users (u_name, u_pass, is_active, is_admin, is_editor, is_viewer) values ('

            check_user=engine.execute(user_sql)
            get_user=check_user.fetchone()
            if get_user is not None:
                MsgBox.critical(self, 'Error creating user','User name already in use')
                pass
            else:
                
                insert_audit_sql='insert into audit (e_type, e_text, date, operator) values ("[USER ADD]","New user created:' + user_name + '",datetime(\'now\'),"' + Window.logged_user + '")'
                engine.execute(insert_audit_sql)

                if user_role==1:
                    sql_values='"' + user_name + '","' + user_pass + '","' + str(user_isactive) + '","1","0","0")'
                    if(engine.execute(add_user_sql+sql_values)):
                        self.a_uname.setText('')
                        self.a_password.setText('')
                        MsgBox.information(self,'Add user', 'User with Admin role was added succesfuly')
                if user_role==2:
                    sql_values='"' + user_name + '","' + user_pass + '","' + str(user_isactive) + '","0","1","0")'
                    if(engine.execute(add_user_sql+sql_values)):
                        MsgBox.information(self,'Add user', 'User with Editor role was added succesfuly')
                if user_role==3:
                    sql_values='"' + user_name + '","' + user_pass + '","' + str(user_isactive) + '","0","0","1")'
                    if(engine.execute(add_user_sql+sql_values)):
                        MsgBox.information(self,'Add user', 'User with Viewer role was added succesfuly')

class Window(QtWidgets.QMainWindow):
    #user_class=0
    logged_user=''
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        uic.loadUi('ui/main.ui', self)
        #self.MplWidget=mplwidget

        if config_parse.get('ENDPOINT','get_mqtt')=='false':
            pass
        else:
            self.statusBar().showMessage('Starting MQTT endpoint')

        if config_parse.get('ENDPOINT','get_serial')=='false':
            pass
        else:
            self.statusBar().showMessage('Starting SERIAL endpoint')

        self.GetValues = UpdateThread()
        #self.GetLog.str_signal.connect(self.WLOG.append)
        get_lbl_sql = 'select * from instant'
        get_lbl_res=engine.execute(get_lbl_sql)
        for r_ in get_lbl_res:
            exec('self.GetValues.' + r_[1] + '.connect(self.' + str(r_[1]) + '.display)')
            exec('self.GetValues.' + r_[1] + '_css.connect(self.' + str(r_[1]) + '.setStyleSheet)')

        self.GetValues.update_status_bar.connect(self.statusbar.showMessage)
        self.GetValues.start()
        self.action_Add_user.triggered.connect(self.AddNewUser)
        self.action_Show_users.triggered.connect(self.EditExUser)
        self.actionExit.triggered.connect(self.ExitApplication)
        self.setWindowFlags(Qt.FramelessWindowHint)

        #self.addToolBar(NavigationToolbar(self.MplWidget.canvas, self))
        
        ages = [2,5,70,40,30,45,50,45,43,40,44, 
        60,7,13,57,18,90,77,32,21,20,40] 
        ages_n = [22,15,72,40,30,45,50,47,43,40,44, 
        60,7,13,57,22,91,77,34,21,20,40]

        range = (0, 100) 
        bins = 10 

        
        self.MplWidget.canvas.axes.clear()
        #self.MplWidget.canvas.axes.rc('axes', titlesize=SMALL_SIZE)
        self.MplWidget.canvas.axes.hist(ages, bins, range, color = 'green',histtype = 'bar', rwidth = 0.8)
        self.MplWidget.canvas.axes.hist(ages_n, bins, range, color = 'red',histtype = 'bar', rwidth = 0.5)
        #self.MplWidget.canvas.axes.plot(t, cosinus_signal)
        #self.MplWidget.canvas.axes.plot(t, sinus_signal)
        #self.MplWidget.canvas.axes.legend(('V1', 'V2'),loc='upper right')
        #self.MplWidget.canvas.axes.set_title('Sample graph')
        self.MplWidget.canvas.draw()

        self.b = QtWidgets.QPushButton('Yahoo!')
        self.statusbar.addWidget(self.b)
        self.show()
    
    def ExitApplication(self):
        sys.exit(0)

    def AddNewUser(self):
        self.AddUser_UI= AddUser(self)
        self.AddUser_UI.show()
        print (self.logged_user)
    
    def EditExUser(self):
        self.EditUser_UI=EditUser(self)
        self.EditUser_UI.show()
        

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    login = Login()

    if login.exec_() == QtWidgets.QDialog.Accepted:
        
        window = Window()
        

        get_lbl_text='select * from fields'
        lbl_result= engine.execute(get_lbl_text)

        for r_ in lbl_result:
            if r_[3]==1:
                exec ('window.' + r_[1] + '.setText(\'' + r_[2] + '\')')
            if r_[3]==2:
                exec ('window.' + r_[1] + '.setTitle(\'' + r_[2] + '\')')
        if login.handleLogin()==1:
            pass
        if login.handleLogin()==2:
            window.menu_Alerts.setEnabled(True)
            window.menu_Reports.setEnabled(False)
            window.menu_Users.setEnabled(False)
        if login.handleLogin()==3:
            window.menu_Alerts.setEnabled(False)
            window.menu_Reports.setEnabled(False)
            window.menu_Users.setEnabled(False)
        #window.show()
        sys.exit(app.exec_())