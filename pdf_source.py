"""Normalize a PDF directory into source records, without Zotero or network access."""
import hashlib,json
from pathlib import Path

TEXT_FIELDS=('title','date','doi','journal','abstract')
LIST_FIELDS=('authors','tags')

def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def metadata_override(path):
    """An optional paper.pdf.json supplies bibliographic fields, never file paths."""
    sidecar=path.with_name(path.name+'.json')
    if not sidecar.exists():return {}
    if sidecar.is_symlink():raise ValueError(f'Metadata sidecar must not be a symlink: {sidecar}')
    try:record=json.loads(sidecar.read_text(encoding='utf-8'))
    except (ValueError,UnicodeError) as exc:raise ValueError(f'Invalid metadata JSON: {sidecar}') from exc
    if not isinstance(record,dict):raise ValueError(f'Metadata must be an object: {sidecar}')
    unknown=set(record)-set(TEXT_FIELDS+LIST_FIELDS)
    if unknown:raise ValueError(f'Unknown metadata fields {sorted(unknown)}: {sidecar}')
    for key,value in record.items():
        valid=isinstance(value,str) if key in TEXT_FIELDS else isinstance(value,list) and all(isinstance(x,str) for x in value)
        if not valid:raise ValueError(f'Invalid metadata field {key}: {sidecar}')
    return record

def pdf_inventory(directory):
    """IDs follow PDF bytes: renames keep IDs; edited content gets a new ID."""
    if not directory:raise ValueError('Set pdf_dir in config.json or initialize with configure.py --pdf-dir PATH')
    root=Path(directory).expanduser().resolve()
    if not root.is_dir():raise ValueError(f'PDF directory does not exist: {root}')
    paths=sorted(p for p in root.rglob('*') if p.suffix.lower()=='.pdf' and p.is_file() and not p.is_symlink() and not any(x.startswith('.') for x in p.relative_to(root).parts))
    if not paths:raise ValueError(f'No PDFs found in {root}; the existing index was not changed')
    groups={}
    for path in paths:
        digest=file_hash(path)
        groups.setdefault(digest,[]).append((path,metadata_override(path)))
    papers=[]
    import pymupdf
    for digest,copies in sorted(groups.items()):
        # Merge compatible sidecars, rejecting ambiguous metadata on duplicate bytes.
        override={}
        for path,fields in copies:
            for key,value in fields.items():
                if key in override and override[key]!=value:
                    raise ValueError(f'Conflicting {key} metadata for duplicate PDF: {path}')
                override[key]=value
        path=copies[0][0];embedded={};error=None
        try:
            with pymupdf.open(path) as document:
                if document.needs_pass:raise ValueError('Password-protected PDF')
                embedded=document.metadata or {}
        except Exception as exc:error=str(exc)
        title=(embedded.get('title') or '').strip()
        author=(embedded.get('author') or '').strip()
        record={'key':'PDF-'+digest,'title':title or path.stem,'authors':[author] if author else [],
                'date':'','doi':'','journal':'','abstract':'','tags':[],
                'item_type':'document','library_source':'pdf_folder','metadata_quality':'pdf_metadata_unreviewed',
                'metadata_provenance':{'title':'embedded_pdf' if title else 'filename','authors':'embedded_pdf' if author else 'unknown',
                                       **{key:'unknown' for key in ('date','doi','journal','abstract','tags')}},
                'collections':sorted({root.name}|{p.parent.relative_to(root).as_posix() for p,_ in copies if p.parent!=root}),
                'notes':[],'version':digest,'duplicate_paths':[str(p) for p,_ in copies[1:]],
                'attachments':[{'key':'PDF-'+digest,'path':str(path),'exists':True,'bytes':path.stat().st_size,'sha256':digest}]}
        record.update(override)
        record['metadata_provenance'].update({key:'sidecar' for key in override})
        if error:record['metadata_error']=error
        papers.append(record)
    return papers
