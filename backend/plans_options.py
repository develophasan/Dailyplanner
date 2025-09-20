# OPTIONS handlers for all plans endpoints
@api_router.options("/plans/daily")
async def plans_daily_options():
    return {"message": "OK"}

@api_router.options("/plans/daily/{plan_id}")
async def plans_daily_detail_options(plan_id: str):
    return {"message": "OK"}

@api_router.options("/plans/monthly")
async def plans_monthly_options():
    return {"message": "OK"}

@api_router.options("/plans/monthly/{plan_id}")
async def plans_monthly_detail_options(plan_id: str):
    return {"message": "OK"}

@api_router.options("/plans/daily/{plan_id}/portfolio")
async def plans_portfolio_options(plan_id: str):
    return {"message": "OK"}