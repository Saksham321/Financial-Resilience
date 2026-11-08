"""Report missing integration setup without printing credential values."""
import json
from app.core.config import settings


def main():
    providers={}
    for name in ('BANKING','UNDERWRITING','BROWSING','NOTIFICATION'):
        fields=[name+'_API_URL',name+'_API_KEY']
        providers[name]={'missing_settings':[field for field in fields if not getattr(settings,field)],'live_verified':False}
    for name in ('GEMINI','ELEVENLABS'):
        providers[name]={'missing_settings':[] if getattr(settings,name+'_API_KEY') else [name+'_API_KEY'],'live_verified':False}
    report={'providers':providers,
        'lending_terms_missing':[field for field in ('INSTALLMENT_ANNUAL_RATE','INSTALLMENT_FEE') if getattr(settings,field) is None],
        'empathetic_voice_configured':bool(settings.ELEVENLABS_EMPATHETIC_VOICE_ID),
        'note':'Presence of settings is not live verification. No external requests were made.'}
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
