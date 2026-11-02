package main

import (
 "fmt"
 "strconv"
 "strings"
)

type Fill struct { OrderID, MatchID, Role string; Side byte; Volume, Price int }

// Phase-2 rule: T is delivered to the aggressor; E to the resting owner.
func parseOwnFill(f []string, sender string) (Fill, bool) {
 if len(f) < 8 || (f[1] != "E" && f[1] != "T") { return Fill{}, false }
 vol, e1 := strconv.Atoi(f[4]); px, e2 := strconv.Atoi(f[5])
 if e1 != nil || e2 != nil || vol <= 0 || len(f[7]) != 1 { return Fill{}, false }
 aggr := f[7][0]; if aggr != 'B' && aggr != 'S' { return Fill{}, false }
 prefix := sender + ":"
 if strings.HasPrefix(f[2], prefix) { return Fill{f[2], f[6], "incoming", aggr, vol, px}, true }
 if strings.HasPrefix(f[3], prefix) { side := byte('B'); if aggr == 'B' { side = 'S' }; return Fill{f[3], f[6], "resting", side, vol, px}, true }
 return Fill{}, false
}

func quotePrices(bid, ask, tick, half int) (int, int, bool) {
 if bid < 0 || ask <= bid || tick < 1 || half < 1 { return 0, 0, false }
 buy := (bid+ask)/2-half*tick; sell := (bid+ask+1)/2+half*tick
 if buy >= ask { buy = bid }; if sell <= bid { sell = ask }
 return buy, sell, buy < sell
}

func fillKey(x Fill) string { return fmt.Sprintf("%s/%s", x.OrderID, x.MatchID) }
