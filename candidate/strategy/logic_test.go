package main
import "testing"
func TestIncomingAndRestingFills(t *testing.T) {
 a, ok := parseOwnFill([]string{"1","T","QUOTE001:Q000001","OTHER001:X","2","610","42","B"}, "QUOTE001")
 if !ok || a.Side != 'B' || a.Role != "incoming" { t.Fatalf("bad incoming %#v", a) }
 b, ok := parseOwnFill([]string{"1","E","OTHER001:X","QUOTE001:Q000001","3","608","43","S"}, "QUOTE001")
 if !ok || b.Side != 'B' || b.Role != "resting" { t.Fatalf("bad resting %#v", b) }
}
func TestQuotePrices(t *testing.T) { b,a,ok:=quotePrices(753,760,1,2); if !ok||b!=754||a!=759 {t.Fatalf("%d %d %v",b,a,ok)} }
