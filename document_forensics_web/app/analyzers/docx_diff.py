from __future__ import annotations

from typing import Any

def diff_forensic(pre: dict[str, Any], post: dict[str, Any]) -> dict[str, Any]:
    """
    Compares the original forensic analysis with the post-cleaning forensic analysis
    and returns a structured delta indicating what was removed or changed.
    """
    diff = {
        "comments_removed": 0,
        "properties_cleaned": [],
        "unicode_suspects_removed": [],
        "media_removed": 0,
        "revision_history_cleaned": False,
        "custom_xml_removed": 0
    }
    
    # Comments
    pre_comments = pre.get("comments", {}).get("count", 0)
    post_comments = post.get("comments", {}).get("count", 0)
    if pre_comments > post_comments:
        diff["comments_removed"] = pre_comments - post_comments
        
    # App & Core properties
    for prop_type in ["core_properties", "app_properties"]:
        pre_props = pre.get(prop_type, {})
        post_props = post.get(prop_type, {})
        for key, pre_val in pre_props.items():
            if pre_val is not None and post_props.get(key) is None:
                diff["properties_cleaned"].append(f"{prop_type}.{key}")
                
    # Unicode Suspects
    pre_sus = pre.get("unicode_suspects", {})
    post_sus = post.get("unicode_suspects", {})
    for key, count in pre_sus.items():
        if count > post_sus.get(key, 0):
            diff["unicode_suspects_removed"].append(key)
            
    # Media
    pre_media = len(pre.get("media", []))
    post_media = len(post.get("media", []))
    if pre_media > post_media:
        diff["media_removed"] = pre_media - post_media
        
    # Revisions / Track Changes
    pre_rev = pre.get("revision_history", {})
    post_rev = post.get("revision_history", {})
    if pre_rev.get("insertions", 0) > 0 or pre_rev.get("deletions", 0) > 0:
        if post_rev.get("insertions", 0) == 0 and post_rev.get("deletions", 0) == 0:
            diff["revision_history_cleaned"] = True
            
    # Custom XML
    pre_xml = pre.get("custom_xml", {}).get("item_count", 0)
    post_xml = post.get("custom_xml", {}).get("item_count", 0)
    if pre_xml > post_xml:
        diff["custom_xml_removed"] = pre_xml - post_xml

    return diff
