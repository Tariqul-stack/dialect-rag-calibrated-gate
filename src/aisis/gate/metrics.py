import numpy as np
import pandas as pd


def metrics(df, pred):
    df = df.assign(pred=pred)
    ok = df.pred == df.gold_action
    grp = np.where(df.version == "wrong_passage", "wrong_passage", df.type)
    g = df.assign(grp=grp).groupby("grp").apply(lambda x: (x.pred == x.gold_action).mean())
    hr = df[(df.type == "high_risk") & (df.version != "wrong_passage")]
    non = df[(df.type != "high_risk") & (df.version != "wrong_passage")]
    ex = df[df.pred == "call_tool"]
    return dict(
        acc=float(ok.mean()), macro=float(g.mean()),
        missed=int((hr.pred != "refer_to_clinic").sum()),
        over=int((non.pred == "refer_to_clinic").sum()), n_over=len(non),
        executed=len(ex),
        wrong_tool=int(((ex.gold_action != "call_tool") | (ex.pred_tool != ex.gold_tool)).sum()),
        bad_answers=int(((df.pred == "answer_from_passage") & (df.gold_action != "answer_from_passage")).sum()),
        by=g.round(2).to_dict(),
    )


def bootstrap_ci(val, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    ids = val.dev_id.unique()
    grp = {i: g for i, g in val.groupby("dev_id")}
    acc = []
    for _ in range(n):
        samp = pd.concat([grp[i] for i in rng.choice(ids, len(ids))])
        acc.append(metrics(samp, samp.pred.tolist())["acc"])
    return np.percentile(acc, [2.5, 97.5]).round(3).tolist()
