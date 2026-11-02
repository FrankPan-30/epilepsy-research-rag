"""Explicit one-time download of public weights only; never uploads corpus text."""
import json
from huggingface_hub import snapshot_download
from rag import MODEL

REPO='intfloat/multilingual-e5-small'
REVISION='614241f622f53c4eeff9890bdc4f31cfecc418b3'
if __name__=='__main__':
    snapshot_download(REPO,revision=REVISION,local_dir=MODEL,allow_patterns=['model.safetensors','config.json','modules.json','sentence_bert_config.json','special_tokens_map.json','tokenizer.json','tokenizer_config.json','sentencepiece.bpe.model','1_Pooling/config.json'])
    (MODEL/'local_provenance.json').write_text(json.dumps({'repo':REPO,'revision':REVISION,'weights':'model.safetensors'},indent=2),encoding='utf-8')
