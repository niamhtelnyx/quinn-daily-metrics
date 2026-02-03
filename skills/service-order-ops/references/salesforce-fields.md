# Salesforce Field Reference — Service Orders

## Service_Order__c

| Field | Type | Notes |
|---|---|---|
| `Id` | ID | Salesforce record ID |
| `Name` | Text | SO name (typically includes account name) |
| `Stage__c` | Picklist | Signed, Terminated, etc. |
| `Contract_Start_Date__c` | Date | Editable start date |
| `Contract_End_Date__c` | Date | **Formula field** (read-only) = Start + Duration |
| `Contract_Duration__c` | Number | Months |
| `Min_Monthly_Commit__c` | Currency | Static monthly commit amount |
| `Rev_Ops_Approved__c` | Checkbox | Gate field — triggers MMC_webhook when set true |
| `commitment_handler_id__c` | Text | Populated by webhook response. NULL = not sent to CM |
| `Opportunity__c` | Lookup | Related Opportunity |
| `Mission_Control_Account__c` | Text | Org ID for Commitment Manager (`organization_id`) |

## Service_Order_Detail__c (Ramped SOs)

| Field | Type | Notes |
|---|---|---|
| `Service_Order__c` | Lookup | Parent SO |
| `Month__c` | Number | Month number in sequence |
| `Monthly_Commit__c` | Currency | Commit for that month |

## FeedItem (Chatter)

Query by `ParentId` = SO Id to see webhook request/response bodies.

| Field | Notes |
|---|---|
| `Body` | Contains webhook JSON payload or response |
| `CreatedDate` | Timestamp |

## MMC_webhook Flow

- **ApiName**: `MMC_webhook`
- **Trigger**: Record update on Service_Order__c
- **Conditions**: Stage=Signed, Mission_Control_Account≠null, Rev_Ops_Approved=true AND isChanged
- **Response codes**: 201=created, 204=terminated/updated
