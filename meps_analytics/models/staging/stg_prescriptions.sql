{% set years = [2017, 2018, 2019, 2020, 2021] %}

{% for year in years %}
select
    dupersid,
    rxdrgnam                     as drug_name,
    cast(tc1 as integer)         as therapeutic_class_1,
    cast(rxdaysup as integer)    as days_supply,
    cast(rxquanty as float)      as quantity,
    cast(rxxp_x as float)        as total_expenditure,
    cast(perwt_f as float)       as person_weight,
    cast(source_year as integer) as source_year
from {{ source('meps_raw', 'pmed_' ~ year) }}
{% if not loop.last %}union all{% endif %}
{% endfor %}