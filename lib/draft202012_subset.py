"""Hermetic validator for the explicit Draft 2020-12 subset used by Lily schemas."""
from __future__ import annotations
import re

class ValidationError(ValueError): pass
def validate(schema, value, path="$"):
    if not isinstance(schema,dict): raise ValidationError(f"{path}:schema")
    if "const" in schema and value != schema["const"]: raise ValidationError(f"{path}:const")
    if "enum" in schema and value not in schema["enum"]: raise ValidationError(f"{path}:enum")
    typ=schema.get("type")
    kinds=typ if isinstance(typ,list) else [typ] if typ else []
    if kinds and not any(_is(kind,value) for kind in kinds): raise ValidationError(f"{path}:type")
    if isinstance(value,str):
        if "minLength" in schema and len(value)<schema["minLength"]: raise ValidationError(f"{path}:minLength")
        if "pattern" in schema and re.fullmatch(schema["pattern"],value) is None: raise ValidationError(f"{path}:pattern")
    if isinstance(value,int) and not isinstance(value,bool) and "minimum" in schema and value<schema["minimum"]: raise ValidationError(f"{path}:minimum")
    if isinstance(value,list):
        if "minItems" in schema and len(value)<schema["minItems"]: raise ValidationError(f"{path}:minItems")
        if "items" in schema:
            for i,item in enumerate(value): validate(schema["items"],item,f"{path}[{i}]")
    if isinstance(value,dict):
        required=schema.get("required",[])
        if any(key not in value for key in required): raise ValidationError(f"{path}:required")
        properties=schema.get("properties",{})
        if schema.get("additionalProperties") is False and any(key not in properties for key in value): raise ValidationError(f"{path}:additionalProperties")
        for key,item in value.items():
            child=properties.get(key,schema.get("additionalProperties"))
            if isinstance(child,dict): validate(child,item,f"{path}.{key}")
    for child in schema.get("allOf",[]): validate(child,value,path)
    if "anyOf" in schema:
        errors=[]
        for child in schema["anyOf"]:
            try: validate(child,value,path)
            except ValidationError as exc: errors.append(exc)
            else: break
        else: raise ValidationError(f"{path}:anyOf")
    condition=schema.get("if")
    if condition is not None:
        try: validate(condition,value,path)
        except ValidationError: pass
        else:
            if "then" in schema: validate(schema["then"],value,path)
    if "not" in schema:
        try: validate(schema["not"],value,path)
        except ValidationError: pass
        else: raise ValidationError(f"{path}:not")
def _is(kind,value):
    return {"object":isinstance(value,dict),"array":isinstance(value,list),"string":isinstance(value,str),"integer":isinstance(value,int) and not isinstance(value,bool),"boolean":isinstance(value,bool),"null":value is None}.get(kind,False)
