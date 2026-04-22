
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.api import FeatureFlagIn, CountryConfigIn
from app.services.domainx.services import PlatformConfigService

router = APIRouter(prefix="/platform", tags=["platform"])

@router.post("/flags")
def set_flag(payload: FeatureFlagIn, db: Session = Depends(get_db)):
    return PlatformConfigService(db).set_flag(**payload.model_dump())

@router.get("/flags/{code}")
def is_enabled(code: str, environment: str | None = None, tenant_code: str | None = None, country_code: str | None = None, db: Session = Depends(get_db)):
    return {"code": code, "enabled": PlatformConfigService(db).is_enabled(code, environment, tenant_code, country_code)}

@router.post("/country-config")
def set_country_config(payload: CountryConfigIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    country_code = data.pop("country_code")
    return PlatformConfigService(db).set_country_config(country_code, **data)
