% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " settings", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  <h2>Description</h2>
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="save">
    <label>
      Repository description
      <input name="description" value="{{repo['description']}}" maxlength="500" placeholder="Repository description">
    </label>
    <button class="button" type="submit">Save description</button>
  </form>
</section>

% if commit_count == 0 or import_bundle_finalizing:
<section class="panel">
  <h2>Import Git bundle</h2>
  % if import_bundle_finalizing:
    <p class="muted" data-import-bundle-status>{{import_bundle_status_message}}</p>
  % else:
  <p class="muted">Create a bundle from the source repository using 
                   <strong>git bundle create repo.bundle --all</strong>, 
                   then upload it here.</p>
  <form method="post" enctype="multipart/form-data" data-import-bundle-form data-upload-url="/{{repo['owner_username']}}/{{repo['name']}}/settings/import-bundle/chunk">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="import_bundle">
    <label>
      <input name="bundle" type="file" accept=".bundle,application/octet-stream" data-import-bundle-file required>
    </label>
    <p class="muted" data-import-bundle-status hidden></p>
    <button class="button" type="submit">Import bundle</button>
  </form>
  % end
</section>
% end

<section class="panel">
  <h2>Pages</h2>
  % if pages_settings["docs_publishable"]:
    <p class="muted"><strong>Pages URL:</strong> <a href="{{pages_settings['url']}}">{{pages_settings["url"]}}</a></p>
    <form class="panel-heading" method="post">
      {{!csrf_field()}}
      <input type="hidden" name="action" value="update_pages">
      <input type="hidden" name="pages_docs_enabled" value="{{0 if pages_settings['docs_enabled'] else 1}}">
      <div>
        % if pages_settings["docs_enabled"]:
          <p><strong>Published</strong> <small class="muted">(from source: `docs/`)</small></p>
        % else:
          <p><strong>Not published</strong> <small class="muted">(from source: `docs/`)</small></p>
        % end
      </div>
      <button class="button" type="submit">{{"Unpublish Pages" if pages_settings["docs_enabled"] else "Publish Pages"}}</button>
    </form>
  % else:
  <p class="muted"><strong>Pages URL:</strong> <a href="{{pages_settings['url']}}">{{pages_settings["url"]}}</a> <small class="muted">(from source: `root`)</small></p>
  % end

  % if pages_settings["is_user_site_repo"]:
    % if pages_settings["cname_error"]:
      <p class="alert">{{pages_settings["cname_error"]}}</p>
    % elif pages_settings["cname_domain"]:
      % custom_domain = pages_settings["custom_domain"]
      <form class="panel-heading" method="post">
        {{!csrf_field()}}
        <input type="hidden" name="action" value="verify_custom_domain">
        <div>
          <p>
            <strong class="muted">Custom Domain:</strong>
            {{pages_settings["cname_domain"]}}
            % if custom_domain and custom_domain["status"]:
              <small class="muted">{{custom_domain["status"]}}</small>
            % end
            % if custom_domain and custom_domain["verified_at"]:
              <small class="notice">@{{custom_domain["verified_at"]}}.</small>
            % end
          </p>
        </div>
        <button class="button" type="submit">{{"Reverify DNS" if custom_domain and custom_domain["verified_at"] else "Verify DNS"}}</button>
      </form>
      <p class="muted">Create this DNS TXT record before verifying:</p>
      <pre>{{pages_settings["txt_name"]}}
{{pages_settings["txt_value"]}}</pre>
    % else:
      <p class="muted"><strong>Custom Domain:</strong> Add a root CNAME file to this repository to configure a custom domain.</p>
    % end
  % end
</section>

<section class="panel">
  <h2>Contributors</h2>
  % if contributors:
    <ul class="clean-list">
      % for contributor in contributors:
        <li class="panel-heading">
          <span><a href="/{{contributor['username']}}">{{contributor["username"]}}</a> <span class="muted">added {{contributor["contributor_since"]}}</span></span>
          <form class="inline-form" method="post">
            {{!csrf_field()}}
            <input type="hidden" name="action" value="remove_contributor">
            <input type="hidden" name="user_id" value="{{contributor['id']}}">
            <button class="button secondary small" type="submit">Remove</button>
          </form>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No contributors yet.</p>
  % end
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="add_contributor">
    <label>
      Username
      <input name="username" value="{{contributor_username}}" autocomplete="off" placeholder="username">
    </label>
    <button class="button" type="submit">Add contributor</button>
  </form>
</section>

<section class="panel danger-zone">
  <h2>Delete repository</h2>
  <p>This permanently deletes the repository, its issues, pull requests, and Git data.</p>
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="delete">
    <label>
      Type {{repo["name"]}} to confirm
      <input name="confirm_name" autocomplete="off">
    </label>
    <button class="button danger" type="submit">Delete repository</button>
  </form>
</section>
