#!/usr/bin/env python
import pygtk
pygtk.require('2.0')
import gtk
import appindicator
import os
import re
import sys
import pynotify
import glob
import string
import pwd
import time
import threading
import thread

# Conf /etc/vpnc/gvpnc.conf
class VPN:
    def __init__(self, name, addr, vpntype, groupname, grouppwd, login, pwd, list_lan, addrtocheck):
        self.name = name;
        self.addr = addr;
        self.vpntype = vpntype;
        self.groupname = groupname;
        self.grouppwd = grouppwd;
        self.login = login;
        self.pwd = pwd;
        self.list_lan = list_lan;
        self.addrtocheck = addrtocheck;
        #self.print_vpn();
        self.create_peer();
        self.CONNECTED = 0;

    def print_vpn(self):
        print self.name;
        print self.addr;
        print self.vpntype;
        print self.groupname;
        print self.grouppwd;
        print self.login;
        print self.pwd;
        for i in range(len(self.list_lan)):
            print self.list_lan[i];

    def pingTestDevice(self):
        while 1:
            time.sleep(1);
            cmd = "ping -q -c2 "+self.addrtocheck+" | grep loss | cut -d' ' -f6 | cut -d'%' -f1 > /tmp/testping.txt"
            os.system(cmd);
            fh = open('/tmp/testping.txt', 'r');
            result = string.atoi(fh.read());
            if (result == 100):
                #print "Reconnexion";
                return -1;
            fh.close();
        return 0;

    def create_peer(self):
        if (self.vpntype == "PPTP"):
            fh = open('/etc/ppp/peers/gvpnc.'+self.name, 'w');
            fh.write('# generated by gvpnc. Do not edit it.\n');
            fh.write('# profile: gvpnc.'+self.name+'\n');
            fh.write('\n');
            fh.write('\n');
            fh.write('# name of tunnel, used to select lines in secrets files\n');
            fh.write('remotename gvpnc.'+self.name+'\n');
            fh.write('\n');
            fh.write('# name of tunnel, used to name /var/run pid file\n');
            fh.write('linkname gvpnc.'+self.name+'\n');
            fh.write('\n');
            fh.write('# name of tunnel, passed to ip-up scripts\n');
            fh.write('ipparam gvpnc.'+self.name+'\n');
            fh.write('\n');
            fh.write('# data stream for pppd to use\n');
            fh.write('pty "/usr/sbin/pptp --loglevel 2 '+self.addr+' --nolaunchpppd"\n');
            fh.write('\n');
            fh.write('# domain and username, used to select lines in secrets files\n');
            fh.write('name "'+self.login+'"\n');
            fh.write('\n');
            fh.write('# use MPPE encryption\n');
            fh.write('require-mppe\n');
            fh.write('#nomppe-stateful\n');
            fh.write('#require-mppe-128\n');
            fh.write('\n');
            fh.write('# we do not require the peer to authenticate itself\n');
            fh.write('noauth\n');
            fh.write('\n');
            fh.write('# we want to see what happen\n');
            fh.write('#nodetach\n');
            fh.write('\n');
            fh.write('# lock the device\n');
            fh.write('lock\n');
            fh.write('\n');
            fh.write('# Do not use BSD compression\n');
            fh.write('nobsdcomp\n');
            fh.write('\n');
            fh.write('# Do not use deflate method\n');
            fh.write('nodeflate\n');
            fh.write('\n');
            fh.write('# do not replace defaultroute\n');
            fh.write('defaultroute\n');
            fh.write('# default MTU\n');
            fh.write('mtu 1500\n');
            fh.write('\n');
            fh.write('# default MRU\n');
            fh.write('mru 1500\n');
            fh.write('\n');
            fh.write('# kernel level debug\n');
            fh.write('kdebug 0\n');
            fh.write('# refuse EAP\n');
            fh.write('refuse-eap\n');
            fh.write('refuse-pap\n');
            #fh.write('# adopt defaults from the pptp-linux package\n');
            #fh.write('file /etc/ppp/options.pptp\n');
            fh.write('#refuse-chap\n');
            fh.write('# use mschap\n');
            fh.write('refuse-mschap\n');
            #fh.write('require-mschap-v2\n');        
            fh.close();
            
            file_r = open('/etc/ppp/chap-secrets', 'r')
            newlines = []
            match = 0;
            for line in file_r.readlines():
                if (re.match(r"^(.+) gvpnc."+self.name+" (.+)", line)):
                    newlines.append('"'+self.login+'" gvpnc.'+self.name+' "'+self.pwd+'"\n');
                    match = 1;
                else:
                    newlines.append(line)
            file_r.close();
            if (match ==0):
                newlines.append('"'+self.login+'" gvpnc.'+self.name+' "'+self.pwd+'"\n');

            file_w = open('/etc/ppp/chap-secrets', 'w')
            file_w.writelines(newlines)
            
        else:
            fh = open('/etc/vpnc/'+self.name+'.conf', 'w');
            fh.write('IPSec gateway '+self.addr+'\n');
            fh.write('IPSec ID '+self.groupname+'\n');
            fh.write('IPSec secret '+self.grouppwd+'\n');
            fh.write('IKE Authmode psk\n');
            fh.write('Xauth username '+self.login+'\n');
            fh.write('Xauth password '+self.pwd+'\n');
            fh.write('Target networks ');
            for i in range(len(self.list_lan)):
                fh.write(self.list_lan[i]+' ');
            fh.write('\n');
            fh.close();

    def connect(self):
        self.timeout = 10;
        print "Connexion a "+self.name;
        if (self.vpntype == "PPTP"):
            cmd = '/usr/sbin/pppd call gvpnc.'+self.name;
        else:
            cmd = '/usr/sbin/vpnc-connect '+self.name;
        os.system(cmd);
        timeout = 0;
        while ((self.check_connection_dev() != 1) and (timeout!=self.timeout)):
            print timeout;
            time.sleep(1);
            timeout = timeout + 1;
        if (timeout == 3):
            return 0;
        timeout = 0;
        while ((self.check_connection() != 1) and (timeout!=self.timeout)):
            print timeout;
            time.sleep(1);
            timeout = timeout + 1;
        if (timeout == self.timeout):
            return 0;
        if (self.vpntype == "PPTP"):
            self.create_routes();
        self.CONNECTED = 1;
        print "Connexion OK";
        self.child_pid = os.fork()
        if self.child_pid == 0:
            res = self.pingTestDevice();
            if (res == -1):
                print "Reconnexion";
                self.connect();
                exit(0);
        return 1;

    def disconnect(self):
        print "Deconnexion de "+self.name;
        if (self.vpntype == "PPTP"):
            cmd = 'poff gvpnc.'+self.name;
        else:
            cmd = 'vpnc-disconnect';
        os.system(cmd);
        self.CONNECTED = 0;
        cmd = "kill "+str(self.child_pid);
        print "PID : "+cmd;
        os.system(cmd);

    def check_connection_dev(self):
        path = "/sys/class/net";
        tab = os.listdir(path);
        if (self.vpntype == "PPTP"):    
            for file in tab:
                if (re.match(r"ppp(\d)", file)):
                    self.device = file;
                    return 1;
        else:
            for file in tab:
                if (re.match(r"tun(\d)", file)):
                    self.device = file;
                    return 1;            
        return 0;     

    def check_connection(self):
        path = "/tmp/check_vpn.sh";
        fh = open(path,'w');
        fh.write('ifconfig | grep '+self.device+'\n');
        fh.write('echo $? > /tmp/status_vpn.log\n');
        fh.close();    
        os.system("sh "+path);
        fh = open('/tmp/status_vpn.log');    
        status = string.atoi(fh.read());
        fh.close();
        if (status != 0):
            return 0;
        else:
            return 1;

    def create_routes(self):
        if (self.vpntype == "PPTP"):
            for i in range(len(self.list_lan)):
                cmd = 'route add -net '+self.list_lan[i]+' dev '+self.device;
                print "lan "+self.list_lan[i]+" "+cmd;
                os.system(cmd);

class gVPN:
    def load_settings(self):
        fh = open('/etc/vpnc/gvpnc.conf', 'r')
        f=fh.readlines();
        #ligne = f.split('\n')
        i=0;
        nbparam = 9;
        while (re.match(r"^\[(\w+)\]", f[i*nbparam]) is not None):
            list_lan=[];
            m = re.match(r"^\[(\w+)\]", f[i*nbparam]);
            name = m.groups(0)[0];
            words = f[i*nbparam+1].split('\n');
            inf = words[0].split('=',1);
            addr = inf[1];
            words = f[i*nbparam+2].split('\n');
            inf = words[0].split('=',1);
            vpntype = inf[1];
            words = f[i*nbparam+3].split('\n');
            inf = words[0].split('=',1);
            groupname = inf[1];
            words = f[i*nbparam+4].split('\n');
            inf = words[0].split('=',1);
            grouppwd = inf[1];
            words = f[i*nbparam+5].split('\n');
            inf = words[0].split('=',1);
            login = inf[1];
            words = f[i*nbparam+6].split('\n');
            inf = words[0].split('=',1);
            pwd = inf[1];
            words = f[i*nbparam+7].split('\n');
            inf = words[0].split('=',1);
            inflan = inf[1].split(';');
            words = f[i*nbparam+8].split('\n');
            inf = words[0].split('=',1);
            addrtocheck = inf[1];
            for j in range(len(inflan)):
                list_lan.append(inflan[j]);
            #print "infos :"+name+" "+addr+" "+vpntype+" "+groupname+" "+grouppwd+" "+login+" "+pwd;
            vpn = VPN(name, addr, vpntype, groupname, grouppwd, login, pwd, list_lan, addrtocheck)
            self.list_VPN.append(vpn);
            i = i+1;
            if (len(f) <= nbparam*i):
                break;
        fh.close()
    
    def connect_clicked(self, widget, data=None):
        for i in range(len(self.list_VPN)):
            if ( self.list_VPN[i].name ==  self.vpn_selected):
                self.statusIcon.set_from_file("pixmaps/connected.png");
                if (self.list_VPN[i].connect() == 1):
                    self.VPN_connected = self.list_VPN[i];
                    self.button_disconnect.set_sensitive(True);
                    self.button_connect.set_sensitive(False);
                    #self.window.set_icon_from_file('pixmaps/connect_established.png');
                    self.statusIcon.set_from_file("pixmaps/connected.png");
                    self.window.set_icon_from_file('pixmaps/connected.png');
                    self.label_status.set_text("Connecte a "+self.list_VPN[i].name);
                else:
                    self.statusIcon.set_from_file("pixmaps/disconnected.png");
                    md = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, "Erreur : impossible de se connecter")
                    md.run()
                    md.destroy()
            #self.list_VPN[i].addr, self.list_VPN[i].vpntype, "", True]);
    
    def disconnect_clicked(self, widget, data=None):
        self.VPN_connected.disconnect();
        self.button_disconnect.set_sensitive(False);
        self.button_connect.set_sensitive(True);
        self.statusIcon.set_from_file("pixmaps/disconnected.png");
        self.window.set_icon_from_file('pixmaps/disconnected.png');
        self.label_status.set_text("Deconnecte");
    
    def on_menuitem_modify_activate(self, widget, data=None):
        for i in range(len(self.list_VPN)):
            if ( self.list_VPN[i].name ==  self.vpn_selected):
                vpn = self.list_VPN[i];
        if (vpn == None):
            return;
        window = gtk.Window ();
        self.window.set_sensitive(False);
        #self.assistant = gtk.Window(gtk.WINDOW_TOPLEVEL);
        window.set_position(gtk.WIN_POS_CENTER);
        #self.windowmod.set_resizable(False); 
        window.set_default_size(420, 300);
        window.connect("delete_event", self.delete_event_win_settings) 
        notebook = gtk.Notebook()
        
        # GENERAL
        fixed_gen = gtk.Fixed();
        label_Nom = gtk.Label("Nom de la connexion");
        self.entry_Nom_Mod = gtk.Entry(max=25);
        self.entry_Nom_Mod.set_text(vpn.name);
        label_Addr = gtk.Label("Adresse IP");
        self.entry_Addr_Mod = gtk.Entry(max=25);
        self.entry_Addr_Mod.set_text(vpn.addr);
        label_GrpName = gtk.Label("Nom du Groupe");
        self.entry_GrpName_Mod = gtk.Entry(max=25);
        self.entry_GrpName_Mod.set_text(vpn.groupname);
        label_GrpPwd = gtk.Label("Mot de passe du Groupe");
        self.entry_GrpPwd_Mod = gtk.Entry(max=25);
        self.entry_GrpPwd_Mod.set_visibility(False);
        self.entry_GrpPwd_Mod.set_text(vpn.grouppwd);
        label_Login = gtk.Label("Login");
        self.entry_Login_Mod = gtk.Entry(max=25);
        self.entry_Login_Mod.set_text(vpn.login);
        label_Mdp = gtk.Label("Mot de passe");
        self.entry_Mdp_Mod = gtk.Entry(max=25);
        self.entry_Mdp_Mod.set_visibility(False);
        self.entry_Mdp_Mod.set_text(vpn.pwd);
        label_Net = gtk.Label("Reseaux Distants");
        self.entry_Net_Mod = gtk.Entry(max=255);
        label_Addrtocheck = gtk.Label("Adresse a tester");
        self.entry_Addrtocheck_Mod = gtk.Entry(max=255);
        self.entry_Addrtocheck_Mod.set_text(vpn.addrtocheck);
        str = "";
        for i in range(len(vpn.list_lan)):
            str = str+vpn.list_lan[i]+" ";
        self.entry_Net_Mod.set_text(str);
        # Par default :
        if (vpn.vpntype == "PPTP"):
            self.entry_GrpName_Mod.set_sensitive(False);
            self.entry_GrpPwd_Mod.set_sensitive(False);
        fixed_gen.put(self.entry_Nom_Mod, 240 , 5);
        fixed_gen.put(self.entry_Addr_Mod, 240 , 35);
        fixed_gen.put(self.entry_GrpName_Mod, 240 , 65);
        fixed_gen.put(self.entry_GrpPwd_Mod, 240 , 95);
        fixed_gen.put(self.entry_Login_Mod, 240 , 125);
        fixed_gen.put(self.entry_Mdp_Mod, 240 , 155);
        fixed_gen.put(self.entry_Net_Mod, 240 , 185);
        fixed_gen.put(self.entry_Addrtocheck_Mod, 240 , 215);
        
        fixed_gen.put(label_Nom, 20 , 5+5);
        fixed_gen.put(label_Addr, 20 , 35+5);
        fixed_gen.put(label_GrpName, 20 , 65+5);
        fixed_gen.put(label_GrpPwd, 20 , 95+5);
        fixed_gen.put(label_Login, 20 , 125+5);
        fixed_gen.put(label_Mdp, 20 , 155+5);
        fixed_gen.put(label_Net, 20, 185+5);       
        fixed_gen.put(label_Addrtocheck, 20, 215+5);
        
        # ADVANCED
        fixed_adv = gtk.Fixed();
               
        label = gtk.Label("General");
        notebook.append_page(fixed_gen, label)
        label = gtk.Label("Avance");
        #notebook.append_page(fixed_adv, label)       
        fixed = gtk.Fixed();
        fixed.put(notebook,0,0);
        butt_save = gtk.Button(stock=gtk.STOCK_SAVE)
        butt_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        butt_cancel.connect("clicked", self.delete_event_win_settings, "Cancel") 
        fixed.put(butt_save, 110, 275);
        fixed.put(butt_cancel, 220, 275);
        window.add(fixed)
        window.show_all();
    
    def on_menuitem_delete_activate(self, widget, data=None):
        print "menu delete"
        #(model, iter) = self.treeselection.get_selected()
        #self.liststore.remove(iter)
        #fh = open('./clickndial_directory.txt', 'w')
        #iter = model.get_iter_root()   
        #iter = model.iter_next(iter_root)
        #while (iter != None):
        #    fh.write(model.get_value(iter,0)+'|'+
        #             model.get_value(iter,1)+'\n')
        #    iter = model.iter_next(iter)
        #fh.close()
        
    def delete_event_win_settings(self, widget, event, data=None):
        self.window.set_sensitive(True);
        widget.hide();    
        #self.assistant.hide();
        return False 

    def callback_radioButton(self, widget, data=None):
        #print "%s was toggled %s" % (data, ("OFF", "ON")[widget.get_active()])
        if ( data == "VPNC" and widget.get_active() ):
            self.VPNC = 1;
            self.PPTP = 0;
            self.assistant.set_page_title(self.assisVPNfixed, "Configuration de la connexion VPNC");
            self.entry_GrpName.set_sensitive(True);
            self.entry_GrpPwd.set_sensitive(True);            
        if ( data == "PPTP" and widget.get_active() ):
            self.PPTP = 1;
            self.VPNC = 0;
            self.assistant.set_page_title(self.assisVPNfixed, "Configuration de la connexion PPTP");
            self.entry_GrpName.set_sensitive(False);
            self.entry_GrpPwd.set_sensitive(False);

    def assistant_apply(self, widget, data=None):
        print "apply "+self.entry_Net.get_text();
        #self.entry_Nom  self.entry_Addr self.entry_GrpName  self.entry_Login self.entry_Mdp
        if ( self.PPTP == 1 ):
           print "PPTP";           
           vpn = VPN(self.label_Verif_Nom.get_text(), 
                     self.label_Verif_Addr.get_text(), 
                     "PPTP", 
                     "",
                     "",
                     self.label_Verif_Login.get_text(), 
                     self.label_Verif_Mdp.get_text(), 
                     self.list_lan);
           self.list_VPN.append(vpn);
        if ( self.VPNC == 1 ):
           print "VPNC";
           vpn = VPN(self.label_Verif_Nom.get_text(), 
                     self.label_Verif_Addr.get_text(), 
                     "VPNC", 
                     self.label_Verif_GrpName.get_text(),
                     self.label_Verif_GrpPwd.get_text(),
                     self.label_Verif_Login.get_text(), 
                     self.label_Verif_Mdp.get_text(), 
                     self.list_lan);
           self.list_VPN.append(vpn);
        
        self.delete_event_win_settings(self.assistant, "Cancel");
        size = len(self.list_VPN)-1;
        self.liststore.append([self.list_VPN[size].name, self.list_VPN[size].addr, self.list_VPN[size].vpntype, True]);
           
           

    def callback_assistant_confirm(self, widget, page, data=None):
        print "test to confirm ";
        self.list_lan = [];
        cur = self.assistant.get_current_page()
        if (cur == 2):
            self.label_Verif_Nom.set_text(self.entry_Nom.get_text());
            self.label_Verif_Addr.set_text(self.entry_Addr.get_text());
            self.label_Verif_GrpName.set_text(self.entry_GrpName.get_text());
            self.label_Verif_GrpPwd.set_text(self.entry_GrpPwd.get_text());
            self.label_Verif_Login.set_text(self.entry_Login.get_text());
            self.label_Verif_Mdp.set_text(self.entry_Mdp.get_text());
            #self.label_Verif_Net.set_text("Reseaux Distants");
           
            
            tab = re.split('\s+', self.entry_Net.get_text());
            #m = re.match(r"(([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)/24)(\s(([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)/24))*", self.entry_Net.get_text());
            for i in range(len(tab)):
                m = re.match(r"(([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})/([0-9]{1,2}))", tab[i]);
                if (m == None):
                    print "erreur lan";
                else:
                    #print m.group(0);
                    self.list_lan.append(m.group(0));
            str = "";
            for i in range(len(self.list_lan)):
                str = str+self.list_lan[i]+" ";
                print str;
            self.label_Verif_Net.set_text(str);


    def on_menuitem_create_assistant(self, widget, data=None):
        self.assistant = gtk.Assistant ();
        self.window.set_sensitive(False);
        #self.assistant = gtk.Window(gtk.WINDOW_TOPLEVEL);
        self.assistant.set_position(gtk.WIN_POS_CENTER);
        self.assistant.set_resizable(False); 
        self.assistant.set_default_size(400, 300);
        self.assistant.connect("delete_event", self.delete_event_win_settings) 
        self.assistant.connect("cancel", self.delete_event_win_settings, "Cancel")
        
        # Page 1
        self.assisP1fixed = gtk.Fixed();
        self.radioButton_pptp = gtk.RadioButton(group=None, label="PPTP");
        self.radioButton_vpnc = gtk.RadioButton(group=self.radioButton_pptp, label="VPN-Cisco"); 
        self.radioButton_pptp.connect("toggled", self.callback_radioButton, "PPTP")
        self.radioButton_vpnc.connect("toggled", self.callback_radioButton, "VPNC")
        
        self.assisP1fixed.put(self.radioButton_pptp, 10, 40);
        self.assisP1fixed.put(self.radioButton_vpnc, 10, 120);
        self.assistant.append_page(self.assisP1fixed);
        self.assistant.set_page_title(self.assisP1fixed, "Creation de la connexion");      
        self.assistant.set_page_type(self.assisP1fixed, gtk.ASSISTANT_PAGE_INTRO);
        self.assistant.set_page_complete(self.assisP1fixed, True);
        
        # Page 2
        #VPN
        self.assisVPNfixed = gtk.Fixed();
        self.assistant.append_page(self.assisVPNfixed);
        self.assistant.set_page_title(self.assisVPNfixed, "Configuration de la connexion PPTP");
        self.assistant.set_page_type(self.assisVPNfixed, gtk.ASSISTANT_PAGE_CONTENT);
        self.assistant.set_page_complete(self.assisVPNfixed, True);    
        self.label_Nom = gtk.Label("Nom de la connexion");
        self.entry_Nom = gtk.Entry(max=15);
        self.label_Addr = gtk.Label("Adresse IP");
        self.entry_Addr = gtk.Entry(max=15);
        self.label_GrpName = gtk.Label("Nom du Groupe");
        self.entry_GrpName = gtk.Entry(max=15);
        self.entry_GrpName.set_visibility(False);
        self.label_GrpPwd = gtk.Label("Mot de passe du Groupe");
        self.entry_GrpPwd = gtk.Entry(max=15);
        self.label_Login = gtk.Label("Login");
        self.entry_Login = gtk.Entry(max=15);
        self.label_Mdp = gtk.Label("Mot de passe");
        self.entry_Mdp = gtk.Entry(max=15);
        self.entry_Mdp.set_visibility(False);
        self.label_Net = gtk.Label("Reseaux Distants");
        self.entry_Net = gtk.Entry(max=255);
        # Par default :
        self.entry_GrpName.set_sensitive(False);
        self.entry_GrpPwd.set_sensitive(False);
        self.assisVPNfixed.put(self.entry_Nom, 240 , 5);
        self.assisVPNfixed.put(self.entry_Addr, 240 , 35);
        self.assisVPNfixed.put(self.entry_GrpName, 240 , 65);
        self.assisVPNfixed.put(self.entry_GrpPwd, 240 , 95);
        self.assisVPNfixed.put(self.entry_Login, 240 , 125);
        self.assisVPNfixed.put(self.entry_Mdp, 240 , 155);
        self.assisVPNfixed.put(self.entry_Net, 240 , 185);
        
        self.assisVPNfixed.put(self.label_Nom, 20 , 5+5);
        self.assisVPNfixed.put(self.label_Addr, 20 , 35+5);
        self.assisVPNfixed.put(self.label_GrpName, 20 , 65+5);
        self.assisVPNfixed.put(self.label_GrpPwd, 20 , 95+5);
        self.assisVPNfixed.put(self.label_Login, 20 , 125+5);
        self.assisVPNfixed.put(self.label_Mdp, 20 , 155+5);
        self.assisVPNfixed.put(self.label_Net, 20, 185+5);
        
        self.assistant.connect("prepare", self.callback_assistant_confirm, self.assisVPNfixed);
        
        # Page 3
        # SUMMARY
        self.assisSUMVPNfixed = gtk.Fixed();
        self.assistant.append_page(self.assisSUMVPNfixed);
        self.assistant.set_page_title(self.assisSUMVPNfixed, "Confirmation du VPN");
        self.assistant.set_page_type(self.assisSUMVPNfixed, gtk.ASSISTANT_PAGE_CONFIRM);
        self.assistant.set_page_complete(self.assisSUMVPNfixed, True);
        
        self.label_Verif_Nom = gtk.Label("Nom de la connexion");
        self.label_Verif_Addr = gtk.Label("Adresse IP");
        self.label_Verif_GrpName = gtk.Label("Nom du Groupe");
        self.label_Verif_GrpPwd = gtk.Label("Mot de passe du Groupe");
        self.label_Verif_Login = gtk.Label("Login");
        self.label_Verif_Mdp = gtk.Label("Mot de passe");
        self.label_Verif_Net = gtk.Label("Reseaux Distants");
        
        self.assisSUMVPNfixed.put(self.label_Verif_Nom, 80 , 5+5);
        self.assisSUMVPNfixed.put(self.label_Verif_Addr, 80 , 35+5);
        self.assisSUMVPNfixed.put(self.label_Verif_GrpName, 80 , 65+5);
        self.assisSUMVPNfixed.put(self.label_Verif_GrpPwd, 80 , 95+5);
        self.assisSUMVPNfixed.put(self.label_Verif_Login, 80 , 125+5);
        self.assisSUMVPNfixed.put(self.label_Verif_Mdp, 80 , 155+5);
        self.assisSUMVPNfixed.put(self.label_Verif_Net, 80, 185+5);
                
        self.assistant.connect("apply", self.assistant_apply);
        
        self.assistant.show_all();

    def treeview_listvpn_clicked_event(self, widget, event):
        if (event.button == 3):
            self.menu_listvpn.show_all()
            self.menu_listvpn.popup(None, None, None, event.button, event.time)
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            print "double click"
            self.connect_clicked(None, None);

    def treeselection_changed(self, widget, data=None):
        (model, iter) = self.treeselection.get_selected()
        if (iter != None):
            self.vpn_selected = model.get_value(iter, 0)
            

    def delete_event(self, widget, event, data=None):
        return False

    # close the main window
    def destroy(self, widget, data=None):
        gtk.main_quit()

    def popup_menu_status(self, widget, button, timestamp):
        self.menu_status.show_all()
        self.menu_status.popup(None, None, gtk.status_icon_position_menu, button, timestamp, widget)

    def icon_activate(self, widget, data=None):
        if data.flags() & gtk.VISIBLE:
            data.hide()
        else:
            data.show()

    # Init classe
    def __init__(self):
        self.VPNC = 0;
        self.PPTP = 1;
        self.list_VPN = []
        
        self.load_settings();
        
        # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.set_position(gtk.WIN_POS_CENTER)
        #self.window.set_default_size(420, 300)
        self.window.set_resizable(True);
        self.window.set_title("gVPN")
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(0)
        self.window.set_icon_from_file('pixmaps/connect_no.png');
    
        # Test superuser
        cmd = '/usr/bin/whoami > /tmp/gvpn_user';
        os.system(cmd);
        fh = open('/tmp/gvpn_user', 'r')
        user=fh.readlines();
        fh.close()
        #print user[0];
        # Msg error
        if ( user[0] != "root\n" ):
            md = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, "Erreur : l'application doit etre lance avec les privileges adminstrateurs")
            md.run()
            md.destroy()
            gtk.main_quit();  
       
        # StatusIcon
        self.statusIcon = gtk.status_icon_new_from_file("pixmaps/disconnected.png")
        self.statusIcon.connect("activate", self.icon_activate, self.window)
        self.statusIcon.connect("popup-menu", self.popup_menu_status)
        self.menu_status = gtk.Menu()
       
        # create items for the menu - labels, checkboxes, radio buttons and images are supported:
        item = gtk.MenuItem("Deconnecter")
        item.show()
        self.menu_status.append(item)
        image = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        image.connect("activate", self.destroy)
        image.show()
        self.menu_status.append(image)                   
        self.menu_status.show()
        #self.appind.set_menu(self.menu)
    
        # Notebook
        self.notebook = gtk.Notebook()
    
        # Fixed
        self.fixed = gtk.Fixed()
    
        # Boutons
        self.image_connect = gtk.Image()
        self.image_connect.set_from_file("pixmaps/stock_lock.png")
        self.button_connect = gtk.Button()
        self.button_connect.set_image(self.image_connect)
        #self.button_connect.set_sensitive(False)
        self.button_connect.connect("clicked", self.connect_clicked)
        
        self.image_disconnect = gtk.Image()
        self.image_disconnect.set_from_file("pixmaps/stock_lock-open.png")
        self.button_disconnect = gtk.Button()
        self.button_disconnect.set_image(self.image_disconnect)
        self.button_disconnect.set_sensitive(False)
        self.button_disconnect.connect("clicked", self.disconnect_clicked)
        self.fixed.put(self.button_connect, 5, 0);
        self.fixed.put(self.button_disconnect, 55, 0);
        self.label_status = gtk.Label("Deconnecte");
        self.fixed.put(self.label_status, 200, 18);
    
        # menu popup
        self.menu_listvpn = gtk.Menu()
        self.menuitem_modify = gtk.MenuItem("Modifier");
        self.menuitem_modify.connect('activate', self.on_menuitem_modify_activate)
        self.menuitem_delete = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        self.menuitem_delete.connect('activate', self.on_menuitem_delete_activate)
        self.menuitem_add = gtk.ImageMenuItem(gtk.STOCK_ADD)
        self.menuitem_add.connect('activate', self.on_menuitem_create_assistant)
        
        self.menu_listvpn.append(self.menuitem_add)
        self.menu_listvpn.append(self.menuitem_modify)
        self.menu_listvpn.append(self.menuitem_delete)
    
        # List VPNS
        self.liststore = gtk.ListStore(str, str, str, 'gboolean')
        self.treeview = gtk.TreeView(self.liststore)		
        self.tvcolumn = gtk.TreeViewColumn('Nom')
        self.tvcolumn.set_min_width(150)
        self.tvcolumn1 = gtk.TreeViewColumn('Adresse IP')
        self.tvcolumn1.set_min_width(150)
        self.tvcolumn2 = gtk.TreeViewColumn('Type')
        self.tvcolumn2.set_min_width(70)
        
        for i in range(len(self.list_VPN)):
            self.liststore.append([self.list_VPN[i].name, self.list_VPN[i].addr, self.list_VPN[i].vpntype, True]);
        
        self.treeview.append_column(self.tvcolumn)
        self.treeview.append_column(self.tvcolumn1)
        self.treeview.append_column(self.tvcolumn2)
               
        self.treeview.connect("button_press_event", self.treeview_listvpn_clicked_event)
        # create a CellRenderers to render the data
        self.cell = gtk.CellRendererText()
        self.cell1 = gtk.CellRendererText()
        self.cell2 = gtk.CellRendererText()
        
        self.treeselection = self.treeview.get_selection()
        self.treeselection.set_mode(gtk.SELECTION_SINGLE)
        self.treeselection.connect("changed", self.treeselection_changed)       
        
        self.tvcolumn.pack_start(self.cell, True)
        self.tvcolumn1.pack_start(self.cell1, True)
        self.tvcolumn2.pack_start(self.cell2, True)
        self.tvcolumn.set_attributes(self.cell, text=0)
        self.tvcolumn1.set_attributes(self.cell1, text=1)
        self.tvcolumn2.set_attributes(self.cell2, text=2)
        
        label = gtk.Label("Liste des VPN")
        self.notebook.append_page(self.treeview, label)
        self.fixed.put(self.notebook, 0, 50)
        
        self.window.add(self.fixed)

        self.window.show_all()

    def main(self):
        gtk.main()

# If the program is run directly or passed as an argument to the python
# interpreter then create a HelloWorld instance and show it
if __name__ == "__main__":
    gVPN = gVPN()
    gVPN.main()
    
