"""Canonical categories and supervised text tagging from labelled user history.

Models are trained on explicitly labelled transactions, never invented bank data.
Unknown descriptions remain unclassified when data/confidence is insufficient.
No model or personal training text is written to disk or sent to another service.
"""
from collections import Counter

ALIASES = {'transit':'transportation','transport':'transportation','grocery':'groceries',
           'loan payment':'loan payments','household bill':'household bills','utility':'utilities',
           'basic utility':'basic utilities','card withdrawal':'card withdrawals',
           'streaming video':'streaming','fitness wellness':'wellness','cloud storage':'cloud storage',
           'household bills':'household bills','loan payments':'loan payments'}


def canonical_category(value):
    value=' '.join(value.strip().casefold().replace('_',' ').replace('-',' ').split())
    return ALIASES.get(value,value)


def predict_category(merchant, history):
    examples=[(t.merchant,canonical_category(t.category)) for t in history
              if canonical_category(t.category)!='unclassified']
    counts=Counter(label for _,label in examples)
    if len(examples)<6 or len(counts)<2 or min(counts.values())<2:
        return {'category':'unclassified','method':'insufficient_labelled_history','confidence':None}
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import make_pipeline
    model=make_pipeline(TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5)),MultinomialNB(alpha=0.1))
    model.fit([text for text,_ in examples],[label for _,label in examples])
    probabilities=model.predict_proba([merchant])[0]
    best=int(probabilities.argmax());confidence=float(probabilities[best])
    return {'category':str(model.classes_[best]) if confidence>=0.65 else 'unclassified',
            'method':'supervised_tfidf_naive_bayes','confidence':round(confidence,6),
            'training_examples':len(examples)}


def category_similarity(a,b):
    """Jaro-Winkler similarity for normalized category/session tags."""
    a,b=canonical_category(a),canonical_category(b)
    if a==b:
        return 1.0 if a else 0.0
    if not a or not b:
        return 0.0
    radius=max(0,max(len(a),len(b))//2-1)
    matched_a=[False]*len(a);matched_b=[False]*len(b)
    for i,char in enumerate(a):
        for j in range(max(0,i-radius),min(len(b),i+radius+1)):
            if not matched_b[j] and char==b[j]:
                matched_a[i]=True;matched_b[j]=True;break
    matches=sum(matched_a)
    if not matches:
        return 0.0
    left=[c for c,matched in zip(a,matched_a) if matched]
    right=[c for c,matched in zip(b,matched_b) if matched]
    transpositions=sum(x!=y for x,y in zip(left,right))/2
    jaro=(matches/len(a)+matches/len(b)+(matches-transpositions)/matches)/3
    prefix=0
    for x,y in zip(a[:4],b[:4]):
        if x!=y:break
        prefix+=1
    return jaro+prefix*0.1*(1-jaro) if jaro>0.7 else jaro
