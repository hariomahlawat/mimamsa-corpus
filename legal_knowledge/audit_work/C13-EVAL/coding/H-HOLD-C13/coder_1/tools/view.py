import sys, re, glob, os
W="/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-HOLD-C13/coder_1"
PAT=re.compile(r"(we hold|we are of the (considered )?(view|opinion)|is held|hold that|held that|question[s]? (of law|for consideration|that arise|which arise|arising)|point[s]? for (consideration|determination)|issue[s]? (for|that|which) (arise|consideration)|the (short|only|main|core|primary) (question|issue|point)|in our (view|opinion|considered)|we answer|answered|we find no|we conclude|we are unable|cannot be sustained|is not sustainable|we are satisfied|accordingly|consequently, the|in the result|for the reasons)", re.I)
def pages(i):
    f=glob.glob(os.path.join(W,"txt","%03d_*.txt"%i))[0]
    t=open(f).read()
    ps=re.split(r"\n=== PAGE (\d+) ===\n",t)[1:]
    return [(int(ps[k]),re.sub(r"\s+"," ",ps[k+1]).strip()) for k in range(0,len(ps),2)]
def main():
    i=int(sys.argv[1]); mode=sys.argv[2] if len(sys.argv)>2 else "sum"
    P=pages(i)
    if mode=="full":
        a=int(sys.argv[3]); b=int(sys.argv[4])
        for n,t in P:
            if a<=n<=b: print("[p%d] %s"%(n,t))
        return
    head=int(sys.argv[3]) if len(sys.argv)>3 else 1500
    tail=int(sys.argv[4]) if len(sys.argv)>4 else 3000
    print("[p1 HEAD] "+P[0][1][:head])
    seen=0
    for n,t in P:
        for s in re.split(r"(?<=[.?:;])\s+(?=[A-Z0-9(\"'])",t):
            if PAT.search(s) and len(s)<900 and seen<int(os.environ.get("NH","15")):
                print("  [p%d] %s"%(n,s)); seen+=1
    # tail
    acc=[];L=0
    for n,t in reversed(P):
        acc.append((n,t)); L+=len(t)
        if L>=tail: break
    acc.reverse(); s="".join("[p%d] %s "%(n,t) for n,t in acc)
    print("[TAIL] "+s[-tail-40:])
if __name__=="__main__": main()
