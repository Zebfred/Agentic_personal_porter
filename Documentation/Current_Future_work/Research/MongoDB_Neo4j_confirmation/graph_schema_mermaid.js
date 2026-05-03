graph TD
    Hero[Hero: userid] -->|DIRECTED_BY| Artifacts[Artifacts: Origin, Principles, Ambition]
    Hero -->|ADHERES_TO| Pillars[Life Pillars]
    Hero -->|ADHERES_TO| Time[Time Structure]
    
    Time -->|HAS_WEEK| Week
    Week -->|HAS_DAY| Day
    Day -->|HAS_TIME_CHUNK| TC[TimeChunk: 6 per Day]
    
    TC -->|PLANNED_AS| Intent[Intent: Calendar Event]
    TC -->|RECORDED_AS| Actual[Actual: Journal/Confirmed Event]
    
    Intent -->|CLASSIFIED_AS| Pillars
    Actual -->|CLASSIFIED_AS| Pillars
    
    Intent -->|MATCH| Actual
    Intent -->|NOT_MATCH| Detour{Detour Type}
    Detour -->|Valuable| VD[Valuable Detour]
    Detour -->|Detrimental| DD[Detrimental Detour]
