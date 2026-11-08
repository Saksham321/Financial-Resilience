"""Command-line access to source-account features from the comparison project."""
import argparse
import asyncio
import json
from app.api.endpoints.reference_review import Scenario
from app.reference_engines.service import account_review


async def run(args):
    from app.shared.database.session import AsyncSessionLocal, async_engine
    scenario=Scenario(scenario_id=args.scenario,income_reduction_pct=args.income_reduction,
        bills_increase_pct=args.bills_increase,one_off_costs=args.one_off,shock_duration_months=args.duration)
    try:
        async with AsyncSessionLocal() as db:
            review=await account_review(db,args.account_id,scenario.model_dump())
        result={'profile':review['profile'],'metrics':review['metrics']} if args.command=='know' else review['shock'] if args.command=='shock' else review
        print(json.dumps(result,indent=2))
    finally:
        await async_engine.dispose()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['know','shock','audit'])
    parser.add_argument('account_id',type=int)
    parser.add_argument('--scenario',choices=['LAID_OFF_EI','FURNACE_REPAIR','LAID_OFF_AND_BILLS_UP','INFLATION_STAGNATION','CUSTOM'],default='LAID_OFF_EI')
    parser.add_argument('--income-reduction',type=float,default=0)
    parser.add_argument('--bills-increase',type=float,default=0)
    parser.add_argument('--one-off',type=float,default=0)
    parser.add_argument('--duration',type=int,default=6)
    asyncio.run(run(parser.parse_args()))


if __name__=='__main__':
    main()
