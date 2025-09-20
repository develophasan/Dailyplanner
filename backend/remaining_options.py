# All remaining OPTIONS handlers for CORS fix

# Plans Detail
@api_router.options("/plans/daily/{plan_id}")
async def plans_daily_detail_options(plan_id: str):
    return {"message": "OK"}

# Monthly Plans  
@api_router.options("/plans/monthly")
async def plans_monthly_options():
    return {"message": "OK"}

@api_router.options("/plans/monthly/{plan_id}")
async def plans_monthly_detail_options(plan_id: str):
    return {"message": "OK"}

# Matrix Search
@api_router.options("/matrix/search")
async def matrix_search_options():
    return {"message": "OK"}

# Portfolio
@api_router.options("/plans/daily/{plan_id}/portfolio")
async def portfolio_options(plan_id: str):
    return {"message": "OK"}

@api_router.options("/portfolio/{photo_id}")
async def portfolio_delete_options(photo_id: str):
    return {"message": "OK"}