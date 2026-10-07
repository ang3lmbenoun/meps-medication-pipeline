with prescriptions as (

    select * from {{ ref('stg_prescriptions') }}

)

select
    dupersid || '_' || source_year as person_year_id,
    dupersid,
    source_year,
    drug_name,
    therapeutic_class_1,
    (therapeutic_class_1 = 242) as is_mental_health,
    days_supply,
    quantity,
    total_expenditure,
    person_weight
from prescriptions