#####################################################################
# This is the main project module
# Created on: 24 February 2012
# Author: rmd
# Description:
#####################################################################

web_template = """
<HEAD>
<TITLE>Light Control</TITLE>
<SCRIPT TYPE="text/javascript">
function setcolor(colordiv) {
    colordiv.style.margin = "";
    colordiv.style.border = "2px; black;";
    document.forms[0].color.value = colordiv.textContent;
    document.forms[0].submit();
}
</SCRIPT>
</HEAD>
<BODY>
<FORM METHOD="POST">
<TABLE>
<TR>
<TD>Choose Node</TD><TD><SELECT NAME="node">
%(nodes)s
</SELECT></TD>
</TR>
<TR>
<TD>Red</TD><TD><INPUT TYPE="text" NAME="red" VALUE="%(red)d"/></TD>
</TR>
<TR>
<TD>Green</TD><TD><INPUT TYPE="text" NAME="green" VALUE="%(green)d"/></TD>
</TR>
<TR>
<TD>Blue</TD><TD><INPUT TYPE="text" NAME="blue" VALUE="%(blue)d"/></TD>
</TR>
<TR>
<TD>Change Delay</TD><TD><INPUT TYPE="text" NAME="speed" VALUE="%(speed)d"/></TD>
</TR>
<TR>
<TD>Or Choose a Predefined Color:</TD><TD>
<DIV STYLE="height:220;overflow:scroll;border:solid;">---select a color from the list---<br/>
%(colors)s
</DIV></TD>
</TR>
<TR>
<TD COLSPAN="2"><INPUT NAME="set_colors" TYPE="submit" VALUE="Set Colors"/><INPUT NAME="random" TYPE="submit" VALUE="Party Mode!"/>
<!--INPUT TYPE="submit" NAME="quit" VALUE="Stop Server" STYLE="background-color:red;"/-->
</TD>
</TR>
</TABLE>
<input type="hidden" name="color" value=""/>
</FORM>
</BODY>
"""
from colors import colors
import digiweb
import zigbee
from socket import *
import sys
import os
import select
import thread
import re

sd = None
th = None
recvData = {}
exitRequest = False

def colorPage(type, path, headers, args):
    socketVal = {'r': 0, 'g':0, 'b':0}
    nodelist = []
    random_mode = False
    change_speed = 6
    change_speed_changed = False
    
    if args is not None:
        if type == "POST": args = splitargs(args)
        ignrgb = False
        for arg in args.keys():
            argkey = arg.lower()
            argval = args[arg]
            if argval is not None: argval = unquote(argval)
            print "key: "+argkey+" val: "+argval
            if not ignrgb and argkey == "red":
                socketVal['r'] = int(argval)
            elif not ignrgb and argkey == "green":
                socketVal['g'] = int(argval)
            elif not ignrgb and argkey == "blue":
                socketVal['b'] = int(argval)
            elif argkey == "speed":
                change_speed = int(argval)
                change_speed_changed = True
            elif argkey == "color":
                if colors.has_key(argval.lower()):
                    socketVal = colors[argval.lower()]
                    ignrgb = True
            elif argkey == "node":
                nodelist.append(argval)
            elif argkey == "random":
                random_mode = True
            elif argkey == "quit":
                print "Stopping server"
                sd.close()
                exitRequest = True
                sys.exit()
                return (digiweb.TextHtml, "exiting")
    
    if random_mode:
        socketdata = "n"
    else:
        socketdata = "".join([k+str(v) for k,v in socketVal.items()])
    
    if change_speed_changed:
        socketdata += "s"+str(change_speed)
    
    socketdata += "\n"
        
    print "sending "+socketdata
    for node in nodelist:
        try:
            sd.sendto(socketdata, 0, (node, 0xe8, 0xc105, 0x11))
        except:
            print "Failed to send to "+node
                
    nodes = zigbee.get_node_list(False)
    nodeList = ""
    for node in nodes:
        if node.type != "end": continue 
        try:
            nodeline = "<OPTION value='"+node.addr_extended+"'>"+\
                zigbee.ddo_get_param(node.addr_extended, "NI")+\
                "</OPTION>"
            nodeList += nodeline
        except:
            pass
    
    colorList = ""
    ckeys = colors.keys()
    ckeys.sort()
    for c in ckeys:
        comps = colors[c]
        luma=comps['r']*.3 + comps['g']*.59 + comps['b']*.11
        if luma < 128: textcolor = 'white' 
        else: textcolor = 'black'
        colorList += "<DIV style=\"background-color:#%02x%02x%02x;color:%s;text-align:center;margin:2px 0px;cursor:pointer;\" onclick=\"setcolor(this)\">%s</DIV>" % (comps['r'], comps['g'], comps['b'], textcolor, c)
    return (digiweb.TextHtml, web_template % {
            'red':socketVal['r'], 'green':socketVal['g'], 'blue':socketVal['b'],'speed':change_speed,
            'nodes':nodeList, 'colors':colorList })

def splitargs(arglist):
    ret = {}
    for arg in arglist.split("&"):
        argsp = arg.split('=')
        if len(argsp) == 1:argsp.append(None)
        ret[argsp[0]] = argsp[1]
    return ret
    
def monitor_read(sock):
    rlist = [sock]
    while not exitRequest:
        select.select(rlist, [], [])
        payload, addr = sock.recvfrom(8192)
        print "received "+payload+" from "+str(addr)+"\n"
        if not recvData.has_key(addr[0]):
            recvData[addr[0]] = payload
        else:
            recvData[addr[0]] += payload
            
        if len(recvData[addr[0]]) > 500:
            recvData[addr[0]] = recvData[addr[0]][-500:]
    
def unquote(str):
    str = str.replace('+',' ')
    str = re.sub('%[\da-fA-F]{2}', lambda(x) : chr(int(x.group(0)[1:],16)), str)
    return str

if __name__ == "__main__":
    sd = socket(AF_XBEE, SOCK_DGRAM, XBS_PROT_TRANSPORT)
    sd.bind(("", 0xe8, 0, 0))
    sd.setblocking(0)

    th = thread.start_new(monitor_read, (sd,))
    
    hnd = digiweb.Callback(colorPage)
    
    print "ready"
    while True: pass
   
