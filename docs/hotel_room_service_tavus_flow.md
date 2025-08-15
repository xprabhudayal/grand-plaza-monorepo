```mermaid
flowchart TD
    %% Initialization Phase
    A[Start] --> B[Load Environment Variables]
    B --> C[Initialize Logging]
    C --> D[Check API Keys]
    D --> D1[STT: Soniox/Deepgram]
    D --> D2[TTS: Cartesia/Deepgram]
    D --> D3[LLM: Groq]
    D --> D4[Tavus: API Key + Replica ID]
    D --> D5[Backend: API_BASE_URL]
    
    D1 --> E[Initialize Services]
    D2 --> E
    D3 --> E
    D4 --> E
    D5 --> E
    
    E --> E1[Audio Services]
    E --> E2[Tavus Video Service]
    E --> E3[Daily Transport]
    
    E1 --> F[Create Pipeline]
    E2 --> F
    E3 --> F
    
    F --> F1[With Tavus: Input→STT→Context→LLM→TTS→Tavus→Output]
    F --> F2[Without Tavus: Input→STT→Context→LLM→TTS→Output]
    
    F1 --> G[Initialize Flow Manager]
    F2 --> G
    
    %% Session Start Phase
    G --> H[Guest Joins Room]
    H --> I[on_first_participant_joined Handler]
    I --> J[Capture Participant Transcription]
    J --> K[Get Room Context]
    
    K --> K1[Get GUEST_ROOM_NUMBER]
    K1 --> K2[API: /api/v1/guests/room/{room_number}]
    K2 --> K3{Guest Found?}
    K3 -->|Yes| K4[Add to context]
    K3 -->|No| K5[Log warning]
    
    K4 --> L[Add Avatar Context]
    K5 --> L
    
    L --> M[Initialize Flow Manager]
    M --> N[Start at "greeting" node]
    
    %% Conversation Flow
    N --> O[greeting Node]
    O --> O1[System: Professional hotel concierge]
    O --> O2[Task: Greet guest, explain options]
    O --> O3[Functions:]
    O3 --> O31[browse_menu() → menu_browse]
    O3 --> O32[search_items() → show_search_results]
    
    O31 --> P[menu_browse Node]
    P --> P1[System: Menu categories]
    P --> P2[Task: Help navigate]
    P --> P3[Functions:]
    P3 --> P31[select_category() → show_category_items]
    P3 --> P32[search_items() → show_search_results]
    P3 --> P33[add_item_to_order() → item_added]
    P3 --> P34[review_current_order() → order_review]
    
    O32 --> Q[show_search_results Node]
    Q --> Q1[System: Search results]
    Q --> Q2[Task: Show matching items]
    Q --> Q3[Functions:]
    Q3 --> Q31[add_item_to_order() → item_added]
    Q3 --> Q32[search_items() → show_search_results]
    Q3 --> Q33[select_category() → show_category_items]
    Q3 --> Q34[review_current_order() → order_review]
    
    P31 --> R[show_category_items Node]
    R --> R1[System: Category items]
    R --> R2[Task: Display items]
    R --> R3[Functions:]
    R3 --> R31[add_item_to_order() → item_added]
    R3 --> R32[select_category() → show_category_items]
    R3 --> R33[search_items() → show_search_results]
    R3 --> R34[review_current_order() → order_review]
    
    P33 --> S[item_added Node]
    Q31 --> S
    R31 --> S
    
    S --> S1[System: Confirm item]
    S --> S2[Task: Verify addition]
    S --> S3[Functions:]
    S3 --> S31[add_item_to_order() → item_added]
    S3 --> S32[browse_menu() → menu_browse]
    S3 --> S33[review_current_order() → order_review]
    S3 --> S34[confirm_final_order() → order_placed]
    
    P34 --> T[order_review Node]
    Q34 --> T
    R34 --> T
    S33 --> T
    
    T --> T1[System: Review complete order]
    T --> T2[Task: Show all items/prices]
    T --> T3[Functions:]
    T3 --> T31[confirm_final_order() → order_placed]
    T3 --> T32[add_item_to_order() → item_added]
    T3 --> T33[modify_order() → menu_browse]
    T3 --> T34[cancel_order() → order_cancelled]
    
    T31 --> U[order_placed Node]
    U --> U1[System: Thank guest]
    U --> U2[Task: Confirmation]
    U --> U3[Actions:]
    U3 --> U31[Get room number]
    U3 --> U32[Get guest info]
    U3 --> U33[Format order]
    U3 --> U34[API: /orders]
    U3 --> U35[Store order ID]
    U3 --> U36[End conversation]
    
    T34 --> V[order_cancelled Node]
    V --> V1[System: Acknowledge cancellation]
    V --> V2[Task: Polite cancel]
    V --> V3[Actions:]
    V3 --> V31[End conversation]
    
    %% Session End Phase
    U36 --> W[Session End Finally]
    V31 --> W
    
    W --> X[Get Room Number/Session ID]
    X --> Y[Update Session Status]
    Y --> Y1[Via Session ID]
    Y --> Y2[Via Room Number]
    Y1 --> Z[Set Status to COMPLETED]
    Y2 --> Z
    
    Z --> AA[END]
    
    %% Error Handling
    subgraph ErrorHandling [Error Handling]
        BA[API Errors] --> BB[Log details]
        BB --> BC[Continue flow]
        
        CA[Pipeline Errors] --> CB[Log exception]
        CB --> CC[Update status to ERROR]
        CC --> CD[End session]
        
        DA[Cancelled Errors] --> DB[Log cancellation]
        DB --> DC[End normally]
    end
    
    %% Styling
    classDef phase fill:#e1f5fe,stroke:#333,stroke-width:2px;
    classDef node fill:#f3e5f5,stroke:#333,stroke-width:1px;
    classDef action fill:#e8f5e8,stroke:#333,stroke-width:1px;
    classDef error fill:#ffebee,stroke:#333,stroke-width:1px;
    
    class A,H,W,AA phase;
    class O,P,Q,R,S,T,U,V node;
    class O1,O2,P1,P2,Q1,Q2,R1,R2,S1,S2,T1,T2,U1,U2,V1,V2 action;
    class BA,CA,DA error;
```