% selected_ref = get("selected_ref", None)
% ref_options = get("ref_options", [])
% selected_ref_value = get("selected_ref_value", "")
% selected_ref_label = get("selected_ref_label", ref_option_label(selected_ref) if selected_ref else "")
% active_tab = get("repo_active_tab", "")
% show_ref_picker = get("show_ref_picker", False)
% if show_ref_picker and selected_ref and ref_options:
  <div class="ref-picker" data-ref-picker data-ref-search-url="/{{repo['owner_username']}}/{{repo['name']}}/refs/search">
    <button class="ref-picker-toggle" type="button" aria-haspopup="true" aria-expanded="false">
      <span>{{selected_ref_label}}</span>
    </button>
    <div class="ref-picker-menu" data-ref-picker-menu hidden>
      <input class="ref-picker-search" type="search" placeholder="Find a ref..." aria-label="Find a ref" autocomplete="off" data-ref-picker-search>
      <div class="ref-picker-options" role="menu">
        % for option in ref_options:
          % is_selected = option["value"] == selected_ref_value
          <a
            class="ref-picker-option {{'active' if is_selected else ''}}"
            href="{{current_url_with_ref(option['ref'])}}"
            data-ref-picker-option
            data-ref-label="{{option['label'].lower()}}"
            data-ref-initial="{{'true' if option.get('is_initial') else 'false'}}"
            role="menuitem"
            aria-current="{{'page' if is_selected else 'false'}}"
          >
            <span>{{option["label"]}}</span>
            % if is_selected:
              <span class="ref-picker-current">current</span>
            % end
          </a>
        % end
        <div class="ref-picker-empty" data-ref-picker-empty hidden>No refs found</div>
      </div>
      <div class="ref-picker-footer">
        <a class="ref-picker-link {{'active' if active_tab == 'tags' else ''}}" href="/{{repo['owner_username']}}/{{repo['name']}}/tags">Tags</a>
        <a class="ref-picker-link {{'active' if active_tab == 'branches' else ''}}" href="/{{repo['owner_username']}}/{{repo['name']}}/branches">Branches</a>
      </div>
    </div>
  </div>
% end
