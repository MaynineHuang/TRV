#!/usr/bin/env python3
import asyncio, os, random
import nats
URL=os.getenv("NATS_URL","nats://nats:4222");FEED="AAH6";SENDER=os.getenv("HEDGER_SENDER","HEDGE001");Q=os.getenv("SENDER","QUOTE001");T=os.getenv("TAKER_SENDER","PYTKR001")
def kv(s):return dict(x.split("=",1) for x in s.split() if "=" in x)
class H:
 def __init__(self,n):self.n=n;self.p={T:0,Q:0,SENDER:0};self.l=asyncio.Lock();self.i=random.randint(0,9000000);self.bid=self.ask=None
 async def bbo(self,m):
  f=m.data.decode().split()
  try:self.bid=int(f[2]);self.ask=int(f[4])
  except:pass
 async def fill(self,m):
  d=kv(m.data.decode());w=m.subject.split('.')[1]
  try:self.p[w]=int(d['pos'])
  except:return
  async with self.l:await self.hedge()
 async def stat(self,m):
  d=kv(m.data.decode());w=m.subject.split('.')[1]
  try:self.p[w]=int(d['pos'])
  except:return
  async with self.l:await self.hedge()
 async def hedge(self):
  net=sum(self.p.values())
  if not net:return
  side='S' if net>0 else 'B';qty=min(abs(net),4);self.i+=1;oid=f"H{self.i%10000000:07d}"
  if self.bid is None or self.ask is None:return
  px=self.bid-100 if side=='S' else self.ask+100
  try:r=(await self.n.request(f"ex.req.{SENDER}",f"{SENDER} A {FEED} {oid} {side} {qty} {px} F".encode(),timeout=1)).data.decode()
  except Exception as e:print('[hedger] failed',e,flush=True);return
  # The observed exchange returns the actual traded volume in Y <n>; Y 0 is
  # accepted-but-unfilled, not a completed hedge.
  parts=r.split();filled=0
  if len(parts)>=3 and parts[1]=='Y':
   try:filled=int(parts[2])
   except ValueError:pass
  self.p[SENDER]+=(filled if side=='B' else -filled)
  print(f"[hedger] before={net} side={side} qty={qty} reply={r} after={sum(self.p.values())}",flush=True)
async def main():
 n=await nats.connect(URL);h=H(n)
 for s in (T,Q):await n.subscribe(f"desk.{s}.fill",cb=h.fill);await n.subscribe(f"strat.{s}.status",cb=h.stat)
 await n.subscribe(f"ex.bbo.{FEED}",cb=h.bbo)
 print(f"[hedger] watching {T},{Q}",flush=True)
 while True:await asyncio.sleep(3600)
asyncio.run(main())
