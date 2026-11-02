package main

import (
 "fmt"
 "log"
 "math/rand/v2"
 "os"
 "strconv"
 "strings"
 "sync"
 "time"
 "github.com/nats-io/nats.go"
)

type order struct { id string; side byte; price int }
type quoter struct {
 nc *nats.Conn; sender, feed string; clip, maxPos, tick, half, threshold int; minRefresh time.Duration
 mu sync.Mutex; bid, ask, pos int; bbo bool; orders map[byte]order; seen map[string]bool; last time.Time; seq uint64
}
func envInt(k string, d int) int { if n,e:=strconv.Atoi(os.Getenv(k)); e==nil && os.Getenv(k)!="" { return n }; return d }
func env(k,d string) string { if v:=os.Getenv(k);v!="" {return v};return d }
func connect(url string) *nats.Conn { for { nc,e:=nats.Connect(url,nats.Timeout(time.Second),nats.MaxReconnects(-1),nats.ReconnectWait(500*time.Millisecond));if e==nil{return nc};log.Printf("waiting for NATS: %v",e);time.Sleep(500*time.Millisecond) } }
func (q *quoter) oid() string { q.mu.Lock();defer q.mu.Unlock();q.seq++;return fmt.Sprintf("Q%07d",q.seq%10000000) }
func (q *quoter) req(s string)(string,error){m,e:=q.nc.Request("ex.req."+q.sender,[]byte(s),time.Second);if e!=nil{return "",e};return string(m.Data),nil}
func yes(s string) bool { p:=strings.Fields(s);return len(p)>1&&p[1]=="Y" }
func (q *quoter) onBBO(m *nats.Msg){ f:=strings.Fields(string(m.Data));if len(f)<6||f[2]=="-"||f[4]=="-"{return};b,e1:=strconv.Atoi(f[2]);a,e2:=strconv.Atoi(f[4]);if e1!=nil||e2!=nil||b>=a{return};q.mu.Lock();q.bid,q.ask,q.bbo=b,a,true;q.mu.Unlock() }
func (q *quoter) onMD(m *nats.Msg){
 f:=strings.Fields(string(m.Data));q.mu.Lock();defer q.mu.Unlock()
 if len(f)>=3&&f[1]=="C" { for s,o:=range q.orders {if o.id==f[2]{delete(q.orders,s)}};return }
 x,ok:=parseOwnFill(f,q.sender);if !ok||q.seen[fillKey(x)]{return};q.seen[fillKey(x)]=true
 if x.Side=='B'{q.pos+=x.Volume}else{q.pos-=x.Volume};p:=fmt.Sprintf("feed=%s match=%s order=%s side=%c qty=%d price=%d pos=%d role=%s",q.feed,x.MatchID,x.OrderID,x.Side,x.Volume,x.Price,q.pos,x.Role)
 q.nc.Publish("desk."+q.sender+".fill",[]byte(p));log.Printf("fill %s",p)
}
func moved(a,b,n int)bool{if a>b{return a-b>=n};return b-a>=n}
func (q *quoter) cancel(o order){r,e:=q.req(fmt.Sprintf("%s C %s %s",q.sender,q.feed,o.id));if e!=nil{log.Printf("cancel %s: %v",o.id,e);return};if yes(r)||strings.Contains(r,"305"){q.mu.Lock();if x,ok:=q.orders[o.side];ok&&x.id==o.id{delete(q.orders,o.side)};q.mu.Unlock()};log.Printf("cancel %s %s",o.id,r)}
func (q *quoter) add(side byte, px int){id:=q.oid();r,e:=q.req(fmt.Sprintf("%s A %s %s %c %d %d L",q.sender,q.feed,id,side,q.clip,px));if e!=nil{log.Printf("add: %v",e);return};if yes(r){q.mu.Lock();q.orders[side]=order{id,side,px};q.mu.Unlock()};log.Printf("add %s %c %d %s",id,side,px,r)}
func (q *quoter) refresh(){
 q.mu.Lock();if !q.bbo||time.Since(q.last)<q.minRefresh{q.mu.Unlock();return};b,a,pos:=q.bid,q.ask,q.pos;ob,hb:=q.orders['B'];os,hs:=q.orders['S'];q.mu.Unlock()
 buy,sell,ok:=quotePrices(b,a,q.tick,q.half);if !ok{return};allowB,allowS:=pos<q.maxPos,pos>-q.maxPos;if pos>0{allowB=false};if pos<0{allowS=false}
 rb:=(!allowB&&hb)||(allowB&&(!hb||moved(ob.price,buy,q.threshold*q.tick)));rs:=(!allowS&&hs)||(allowS&&(!hs||moved(os.price,sell,q.threshold*q.tick)))
 if !rb&&!rs{return};if rb&&hb{q.cancel(ob)};if rs&&hs{q.cancel(os)};if rb&&allowB{q.add('B',buy)};if rs&&allowS{q.add('S',sell)};q.mu.Lock();q.last=time.Now();q.mu.Unlock()
}
func (q *quoter) status(){q.mu.Lock();s:=fmt.Sprintf("pos=%d bid=%d ask=%d live=%d",q.pos,q.bid,q.ask,len(q.orders));q.mu.Unlock();q.nc.Publish("strat."+q.sender+".status",[]byte(s));log.Printf("status %s",s)}
func main(){
 sender:=env("SENDER","QUOTE001");if len(sender)!=8{log.Fatal("SENDER must be 8 characters")};q:=&quoter{sender:sender,feed:env("QUOTER_FEED","AAH6"),clip:envInt("QUOTER_CLIP",1),maxPos:envInt("QUOTER_MAX_POS",4),tick:1,half:envInt("QUOTER_HALF_SPREAD",2),threshold:envInt("QUOTER_REQUOTE_TICKS",2),minRefresh:time.Duration(envInt("QUOTER_MIN_REFRESH_MS",250))*time.Millisecond,orders:map[byte]order{},seen:map[string]bool{},seq:uint64(rand.IntN(9000000))}
 if q.clip<1||q.maxPos<q.clip||q.threshold<1{log.Fatal("invalid quoter limits")};q.nc=connect(env("NATS_URL","nats://nats:4222"));defer q.nc.Drain()
 if r,e:=q.req(fmt.Sprintf("%s Q %s",q.sender,q.feed));e!=nil{log.Printf("STP: %v",e)}else{log.Printf("STP %s",r)}
 q.nc.Subscribe("ex.bbo."+q.feed,q.onBBO);q.nc.Subscribe("ex.md."+q.feed+"."+q.sender,q.onMD);if e:=q.nc.Flush();e!=nil{log.Fatal(e)};log.Printf("quoter sender=%s feed=%s clip=%d max_pos=%d",q.sender,q.feed,q.clip,q.maxPos)
 r:=time.NewTicker(100*time.Millisecond);s:=time.NewTicker(time.Second);defer r.Stop();defer s.Stop();for{select{case<-r.C:q.refresh();case<-s.C:q.status()}}
}
