dim_suppliers  ──┐
                 │ (1 supplier → many products)
dim_products   ──┤
                 │ (1 product → many shipments)
dim_warehouses ──┼──► fact_shipments ◄── dim_date
                 │    (core event table)
                 │
dim_warehouses ──┘ (origin AND destination — self-join pattern)

dim_products   ──┐
                 ├──► fact_inventory ◄── dim_warehouses
dim_date       ──┘    (daily snapshots)