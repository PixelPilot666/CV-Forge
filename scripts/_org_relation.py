"""Shared validation/rendering rules for verified organization relations."""
import re


ALLOWED_RELATIONS = {
    "group_affiliate", "subsidiary", "parent_company", "brand", "product"
}
CONTROL_RELATIONS = {"group_affiliate", "subsidiary", "parent_company"}
ALLOWED_EVIDENCE_TYPES = {"official_source", "user_confirmation"}
DISPLAY_TEMPLATES = {
    "group_affiliate": "{entity}旗下",
    "subsidiary": "{entity}子公司",
    "parent_company": "母公司：{entity}",
    "brand": "品牌：{entity}",
    "product": "产品：{entity}",
}
ENTITY_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9 .·&+_\-]{0,49}$")
RELATION_TERMS = (
    "旗下", "子公司", "母公司", "控股", "全资", "持股", "隶属", "附属",
    "所属", "实际控制", "集团成员", "成员企业", "关联公司", "所有", "资产",
    "投资企业",
)


def display(relation):
    if not isinstance(relation, dict):
        return ""
    relation_type = relation.get("relation_type")
    entity = (relation.get("entity") or "").strip()
    template = DISPLAY_TEMPLATES.get(relation_type)
    return template.format(entity=entity) if template and entity else ""


def validation_errors(relation):
    """Return field-level errors for one canonical profile org relation."""
    if not isinstance(relation, dict):
        return ["必须是映射(dict)"]
    errors = []
    relation_id = relation.get("id")
    entity = (relation.get("entity") or "").strip()
    relation_type = relation.get("relation_type")
    evidence_type = relation.get("evidence_type")
    evidence = (relation.get("evidence") or "").strip()
    verified_at = (relation.get("verified_at") or "").strip()
    if not (isinstance(relation_id, str) and relation_id.strip()):
        errors.append("id 不能为空")
    if (not ENTITY_RE.fullmatch(entity)
            or any(term in entity for term in RELATION_TERMS)):
        errors.append(
            "entity 必须是 1–50 字符的纯实体名称，不得含括号、分隔符或关系陈述词")
    if relation_type not in ALLOWED_RELATIONS:
        errors.append(f"relation_type「{relation_type}」非法")
    if evidence_type not in ALLOWED_EVIDENCE_TYPES:
        errors.append(f"evidence_type「{evidence_type}」非法")
    if not evidence:
        errors.append("evidence 不能为空")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified_at):
        errors.append("verified_at 必须为 YYYY-MM-DD")
    if relation_type in CONTROL_RELATIONS and evidence_type != "official_source":
        errors.append("控制关系必须以 official_source 核实")
    return errors
