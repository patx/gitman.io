% rebase("base.tpl", title="New pull request", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  % if source_options and target_options:
    <h2>Open pull request</h2>
    <form method="post">
      {{!csrf_field()}}
      <label>
        Source ref
        <select name="source_ref">
          % for option in source_options:
            <option value="{{option['value']}}" {{"selected" if option["value"] == selected_source_ref else ""}}>{{option["label"]}}</option>
          % end
        </select>
      </label>
      <label>
        Target ref
        <select name="target_ref">
          % for option in target_options:
            <option value="{{option['value']}}" {{"selected" if option["value"] == selected_target_ref else ""}}>{{option["label"]}}</option>
          % end
        </select>
      </label>
      <label>
        Title
        <input name="title" value="{{title_value}}" required maxlength="200">
      </label>
      <label>
        Body
        <textarea name="body" rows="8">{{body_value}}</textarea>
      </label>
      <button class="button" type="submit">Open pull request</button>
    </form>
  % elif source_options:
    <p class="empty">This repository has no target branches.</p>
  % else:
    <p class="empty">This repository has no source branches yet.</p>
    <form class="inline-form" method="post" action="/{{repo['owner_username']}}/{{repo['name']}}/fork">
      {{!csrf_field()}}
      <input type="hidden" name="name" value="{{repo['name']}}">
      <input type="hidden" name="description" value="{{repo['description']}}">
      <button class="button" type="submit">Fork repository</button>
    </form>
  % end
</section>
