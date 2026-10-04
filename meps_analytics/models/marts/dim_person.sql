with demographics as (

    select * from {{ ref('stg_demographics') }}

)

select
    dupersid as person_id,
    sex,
    race_ethnicity,
    age_last as age,
    case
        when age_last < 18 then '0-17'
        when age_last between 18 and 34 then '18-34'
        when age_last between 35 and 49 then '35-49'
        when age_last between 50 and 64 then '50-64'
        else '65+'
    end as age_group,
    poverty_category,
    census_region,
    insurance_coverage,
    person_weight
from demographics