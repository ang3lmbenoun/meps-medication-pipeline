with source as (

    select * from {{ source('meps_raw', 'demographics_2021') }}

)

select
    dupersid,
    cast(panel as integer)       as panel,
    cast(agelast as integer)     as age_last,
    cast(age21x as integer)      as age_end_of_year,
    case cast(sex as integer)
        when 1 then 'Male'
        when 2 then 'Female'
    end                          as sex,
    case cast(racethx as integer)
        when 1 then 'Hispanic'
        when 2 then 'White, non-Hispanic'
        when 3 then 'Black, non-Hispanic'
        when 4 then 'Asian, non-Hispanic'
        when 5 then 'Other/Multiple, non-Hispanic'
    end                          as race_ethnicity,
    cast(povcat21 as integer)    as poverty_category,
    cast(region21 as integer)    as census_region,
    cast(inscov21 as integer)    as insurance_coverage,
    cast(perwt21f as float)      as person_weight,
    cast(varstr as integer)      as variance_stratum,
    cast(varpsu as integer)      as variance_psu,
    cast(source_year as integer) as source_year
from source