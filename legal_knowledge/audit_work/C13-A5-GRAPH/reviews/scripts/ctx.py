import subprocess,sys,re
doc,needle,before,after=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
t=subprocess.run(['git','-C','/home/user/c7','show',f'ad77758d:data/text/{doc}.txt'],capture_output=True,text=True).stdout
t=re.sub(r'\s+',' ',t)
i=t.find(needle)
print('len',len(t),'pos',i)
if i>=0: print(t[max(0,i-before):i+after])
