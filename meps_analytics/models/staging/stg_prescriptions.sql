with source as (

    select * from {{ source('meps_raw', 'pmed_2021') }}

)

select
    dupersid,
    rxdrgnam                     as drug_name,
    cast(tc1 as integer)         as therapeutic_class_1,
    cast(rxdaysup as integer)    as days_supply,
    cast(rxquanty as float)      as quantity,
    cast(rxxp21x as float)       as total_expenditure,
    cast(perwt21f as float)      as person_weight,
    cast(source_year as integer) as source_year
from source