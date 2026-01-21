from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

from scraper import run_broker_analysis
from discovery import run_discovery_process

app = FastAPI(
    title="Traded.co Broker Analyzer API",
    description="An API to discover and analyze real estate brokers.",
    version="1.5.0",
)


class BrokerInput(BaseModel):
    name: str
    profile_url: HttpUrl
    company: str


class BrokerOutput(BaseModel):
    Name: str
    FirstName: str
    LastName: str
    JobTitle: str
    CompanyName: str
    LinkedInProfile: Optional[str] = "Not Found"
    TradedLinkToLoan: Optional[str] = None
    TradedLinkToProfile: HttpUrl


class DiscoveryInput(BaseModel):
    states: List[str]
    max_pages_per_state: Optional[int] = 5


class DiscoveredBroker(BaseModel):
    Name: str
    First_Name: str = Field(alias="First Name")
    Last_Name: str = Field(alias="Last Name")
    Location: str
    Traded_Link_to_Profile: str = Field(alias="Traded Link to Profile")
    Company: str
    Job_Title: str = Field(alias="Job Title")
    Business_Email: str = Field(alias="Business Email")
    Mobile_Phone_Number: str = Field(alias="Mobile Phone Number")
    LinkedIn_Profile: Optional[str] = Field("Not Found", alias="LinkedIn Profile")
    Traded_Link_to_Loan: Optional[str] = Field(None, alias="Traded Link to Loan (Non-Stabilized)")

    class Config:
        populate_by_name = True


@app.post("/analyze-brokers", response_model=List[BrokerOutput])
async def analyze_brokers_endpoint(brokers: List[BrokerInput]):
    print(f"Received API request to analyze {len(brokers)} brokers.")
    brokers_to_process = []
    for broker in brokers:
        broker_dict = broker.dict()
        broker_dict['profile_url'] = str(broker_dict['profile_url'])
        brokers_to_process.append(broker_dict)

    try:
        qualified_brokers = run_broker_analysis(brokers_to_process)
        return qualified_brokers
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/discover-brokers", response_model=List[DiscoveredBroker])
async def discover_brokers_endpoint(input_data: DiscoveryInput):
    print(f"Received API request to discover brokers in: {input_data.states}")
    try:
        results = run_discovery_process(input_data.states, input_data.max_pages_per_state)
        return results
    except Exception as e:
        print(f"FATAL ERROR during discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/")
def read_root():
    return RedirectResponse(url="/docs")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)