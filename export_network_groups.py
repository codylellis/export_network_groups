import json 
import subprocess
import traceback
import os
import glob

#input validation
def question(stuff):
    while True:
        answer = input(f"\n{stuff}: ")
        if len(answer) != 0:
            False
            return answer 

#configuration for api/login/domain/cma
def askConfig():

    print("\n[ Provide API/CMA/Domain Configuration ]\n")

    global domainname, grouplist, targetdomain

    domainname = question("Domain Name")
    targetdomain = question("Target Domain Name")
    
    grouplist = []
    while True:
        groups = input(f"\nEnter Group Name to export. Type 'done' to exit.\n")
        if "done" in groups:
            False
            return grouplist
        else: 
            grouplist.append(groups)

# verify user configuration 
def verifyConfig(): 
    formatanswer = f"""Domain Name = {domainname}
Target Domain Name = {targetdomain}
Groups = {grouplist}"""

    result = question(f"\n{formatanswer}\n\nIs this information correct? (y/n) ")   
    if result == "n":
        askConfig()
    elif result == "y": 
        print("\nContinuing... \n")
        print(f"Delete old files...\n")
        os.system(f'rm -v *.txt *.json')
        

# run command on OS 
def runcmd(cmd): 
    result = subprocess.check_output(cmd, shell=True, text=True)
    return result

# get json object from mgmt api
def showgroup(group):
    
    cmd = f"mgmt_cli -r true -d {domainname} show group name {group} details-level full --format json"
    result = runcmd(cmd)
    groupjson = json.loads(result)
    with open(f'{domainname}_{group}_showgroups.json', 'w') as f:
        f.write(json.dumps(groupjson, indent=4, sort_keys=False))

    return groupjson


# parse json object
def parser(data, group): 
    
    global hosts,ranges,networks
    hosts = {}
    ranges = {}
    networks = {}

    try:
        for ip in data['members']: 
            if ip['type'] == 'host':
                hosts[ip['name']] = ip['ipv4-address']
            elif ip['type'] == 'address-range':
                ranges[ip['name']] = ip['ipv4-address-first'], ip['ipv4-address-last']
            elif ip['type'] == 'network':
                networks[ip['name']] = ip['subnet4'], ip['mask-length4']
            else:
                print(f"[ parser ] Mising Object Type: {ip['type']}\n")
                print(f"[ parser ] Screenshot and RFE to Cody Ellis\n")
            
    except Exception as e:
        print(f"[ parser ] Error: {e}\n")
        print(traceback.format_exc())

    pout = hosts, ranges, networks

    with open(f'{domainname}_{group}_parsed.txt', 'a') as f:
        f.write(json.dumps(pout, indent=4, sort_keys=False))

# create host commands
def host(hsts, newdomain, groupname, publish):
    
    empty = []
    
    try:
        for x,y in hsts.items():
            mcli = f'mgmt_cli -r true -d {newdomain} add host name {x} ip-address {y} ignore-warnings'
            empty.append(mcli)
    except Exception as e: 
        print(f"[ host ] Error: {e}\n")
        print(traceback.format_exc())
        
    with open(f'{newdomain}-{groupname}_hosts-config.txt', 'w') as f:
        for items in empty:
            f.write(f"{items}\n")
        f.write(f"{publish}\n")


# create range commands
def rng(rngs, newdomain, groupname, publish): 

    empty = []
    
    try:
        for x,y in rngs.items(): 
            mcli  = f'mgmt_cli -r true -d {newdomain} address-range name {x} ip-address-first {y[0]} ip-address-last {y[1]} ignore-warnings'
            empty.append(mcli)
    except Exception as e: 
        print(f"[ range ] Error: {e}\n")
        print(traceback.format_exc())
    
    with open(f'{newdomain}-{groupname}_ranges-config.txt', 'w') as f:
        for items in empty:
            f.write(f"{items}\n")
        f.write(f"{publish}\n")


# create network commands
def network(nets, newdomain, groupname, publish): 

    empty = []
    
    try:
        for x,y in nets.items(): 
            mcli = f'mgmt_cli -r true -d {newdomain} add network name {x} subnet {y[0]} mask-length {y[1]} ignore-warnings'
            empty.append(mcli)
    except Exception as e: 
        print(f"[ network ] Error: {e}\n")
        print(traceback.format_exc())
    
    with open(f'{newdomain}-{groupname}_networks-config.txt', 'w') as f:
        for items in empty:
            f.write(f"{items}\n")
        f.write(f"{publish}\n")


def output(newdomain, groupname): 
    
    publishstring = f'mgmt_cli -r true -d {newdomain} publish'
    
    if len(hosts) != 0:
        host(hosts, newdomain, groupname, publishstring)
    if len(ranges) != 0:
        rng(ranges, newdomain, groupname, publishstring)
    if len(networks) != 0:
        network(networks, newdomain, groupname, publishstring)


def combinefiles(newdomain, groupname): 
    
    publishstring = f'mgmt_cli -r true -d {newdomain} publish'
    complete = f'{newdomain}-{groupname}_COMPLETE.txt'
    
    listing = glob.glob(f'{newdomain}-{groupname}_*')
    with open(complete, 'w') as f:
        for files in listing: 
            with open(files) as infile:
                for line in infile:
                    f.write(line)
                    
    groupstring = f'mgmt_cli -r true -d {newdomain} add group name {groupname}'
    
    memcount = len(hosts.keys()) + len(ranges.keys()) + len(networks.keys())
    print(f"memcount : {memcount}\n")                
    
    memnames = list(hosts.keys()) + list(ranges.keys()) + list(networks.keys())
    print(f"memnames : {memnames}\n")
    
    with open(complete, 'a') as f:
        for x,y in zip(range(1,memcount+1,1), memnames):
            groupstring += f' members.{x} "{y}"'
        f.write(f'{groupstring}\n{publishstring}\n')
        

def undochanges(newdomain, groupname): 
    
    undo = f'{newdomain}-{groupname}_UNDO.txt'
    publishstring = f'mgmt_cli -r true -d {newdomain} publish'

    hostlist = []
    if len(hosts) != 0:
        for x in hosts.keys():
            dhost = f'mgmt_cli -r true -d {newdomain} delete host name "{x}"'
            hostlist.append(dhost)
    
    rangelist = []       
    if len(ranges) != 0:
        for x in ranges.keys():
            drange = f'mgmt_cli -r true -d {newdomain} delete address-range name "{x}"'
            rangelist.append(drange)
            
    netlist = []
    if len(networks) != 0:
        for x in networks.keys():
            dnet = f'mgmt_cli -r true -d {newdomain} delete network name "{x}"'
            netlist.append(dnet)
            

    dgroup = f'mgmt_cli -r true -d {newdomain} delete group name "{groupname}"'
        
    complist = hostlist + rangelist + netlist
    
    with open(undo, 'w') as f: 
        for item in complist:
            f.write(f'{item}\n')
        f.write(publishstring + '\n')
            
    with open(undo, 'a') as f: 
        f.write(f'{dgroup}\n')
        f.write(publishstring + '\n')
        


def main(): 

    # User Input
    askConfig()
    verifyConfig()


    # Get Network Groups
    for g in grouplist:
        jresult = showgroup(g)
        parser(jresult, g)
        output(targetdomain, g)
        combinefiles(targetdomain, g)
        undochanges(targetdomain, g)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("User ended script\n")
    except Exception as e: 
        print(f"[main] Error: {e}\n")
        print(traceback.format_exc())
    finally:
        quit()