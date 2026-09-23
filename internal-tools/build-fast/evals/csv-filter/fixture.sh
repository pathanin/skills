#!/bin/bash
# Real-shaped input: currency-formatted amounts, one N/A, one blank, a 499.99 near-miss.
cat > orders.csv <<'CSV'
order_id,customer,amount,date
A1001,Nguyen,120.50,2026-08-01
A1002,Okafor,"$1,250.00",2026-08-01
A1003,Silva,499.99,2026-08-02
A1004,Kim,510.00,2026-08-02
A1005,Haddad,N/A,2026-08-03
A1006,Petrov,75.25,2026-08-03
A1007,Mensah,"$2,040.10",2026-08-04
A1008,Tanaka,860.00,2026-08-04
A1009,Rossi,,2026-08-05
A1010,Dubois,501.01,2026-08-05
A1011,Ali,300.00,2026-08-06
A1012,Novak,"$999.90",2026-08-06
A1013,Garcia,15.00,2026-08-07
A1014,Chen,733.33,2026-08-07
CSV
