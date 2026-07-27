"""Closed-world validator for a future B7.7-authorized real-result report; fixtures only here."""
from __future__ import annotations
import json
from pathlib import Path
from lib.io import relative_to_root
TOP={'schema_version','order_id','hypothesis_id','rerun_id','evidence_tier','edge_claim','producing_git_commit','gate_sha256','runner_sha256','container_identity','schedule_attestation','ledger','observation_counts','primary_statistics','realized_confirmation','side_effects','regimes','validation_seal','decision','mechanism_autopsy'}
def validate_report(report:dict)->dict:
 b=[f'unknown:{x}' for x in set(report)-TOP]+[f'missing:{x}' for x in TOP-set(report)]
 for key,value in {'schema_version':'lily_l3_corrected_rerun_falsification_report_v2','order_id':'B7.7','hypothesis_id':'L-3','evidence_tier':'E1','edge_claim':'none'}.items():
  if report.get(key)!=value:b.append(f'mismatch:{key}')
 counts=report.get('observation_counts',{}); primary=report.get('primary_statistics',{}); side=report.get('side_effects',{})
 if not isinstance(counts,dict) or counts.get('mintrl_falsify')!=49 or counts.get('effective_independent_bets',0)<0 or any(counts.get(k)!=1 for k in ('asset_multiplier','day_multiplier','trade_multiplier','t20_multiplier')):b.append('observation_or_funding_contract_invalid')
 funded=isinstance(counts,dict) and counts.get('effective_independent_bets',0)>=49
 if report.get('decision')=='falsified' and (not funded or not isinstance(primary,dict) or primary.get('ucb') is None or (primary['ucb']>=.05 and side.get('met') is not False)):b.append('falsification_decision_inconsistent')
 if report.get('decision')=='not_falsified_not_validated' and not funded:b.append('not_falsified_without_funding')
 if not isinstance(side,dict) or side.get('evaluable') is not True or side.get('cost_alias_turnover') is not False:b.append('side_effects_not_evaluable_or_cost_alias')
 if report.get('regimes',{}).get('pooled') is True or report.get('regimes',{}).get('inferential_claim_funded') is False and report.get('regimes',{}).get('claims'):b.append('regime_contract_invalid')
 if report.get('validation_seal',{}).get('status')!='sealed_not_accessed':b.append('validation_opened')
 if report.get('decision')=='falsified' and (not isinstance(report.get('mechanism_autopsy'),dict) or not report['mechanism_autopsy'].get('implementation_data_alternatives')):b.append('autopsy_incomplete')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
