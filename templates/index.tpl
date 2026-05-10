% rebase("base.tpl", title="GitMan activity", user=user, error=error, notice=notice)

<section class="panel" style="border-bottom: none;">
  <div class="panel-heading">
    <div>
            <p class ="eyebrow">GitMan.io</p>
            <h1>Free Git repository hosting for open source software</h1>
            % if not user:
              <div class="hero-actions" style="margin-bottom:50px;">
                <a class="button" href="/signup">Create an account</a>
                <a class="button secondary" href="/login">Log in</a>
              </div>
            % else:
              <div class="hero-actions" style="margin-bottom:50px;">
              <div class="repo-search" data-repo-search data-repo-search-url="/-/repos/search">
                <input
                  id="repo-search-input"
                  class="repo-search-input"
                  type="search"
                  placeholder="Search all repositories"
                  autocomplete="off"
                  data-repo-search-input
                  aria-haspopup="listbox"
                  aria-expanded="false"
                  aria-controls="repo-search-results"
                >
                <div id="repo-search-results" class="repo-search-menu" role="listbox" data-repo-search-results hidden>
                  <p class="repo-search-empty" data-repo-search-empty hidden>No repositories found.</p>
                </div>
              </div>
              </div>
            % end
    </div>
  </div>

  % if actions:
        <h1>Recent Activity Feed</h1>
    <ol class="activity-feed">
      % for action in actions:
        % repo_url = "/" + action["repo_owner_username"] + "/" + action["repo_name"] if action["repo_owner_username"] and action["repo_name"] else ""
        % show_repo_context = repo_url and action["target_url"] != repo_url
        <li>
          <p class="activity-title">
            % if action["actor_url"]:
              <strong><a href="{{action['actor_url']}}">{{action["actor_label"]}}</a></strong>
            % else:
              <strong>{{action["actor_label"]}}</strong>
            % end
            {{action["summary"]}}
            <a href="{{action['target_url']}}">{{action["target_label"]}}</a>
          </p>
          <p class="muted">
            % if show_repo_context:
              in <a href="{{repo_url}}">{{action["repo_owner_username"]}}/{{action["repo_name"]}}</a> ·
            % end
            {{action["occurred_at"]}}
          </p>
          % if action["detail"]:
            <p class="activity-detail">{{!render_markdown_links(action["detail"])}}</p>
          % end
        </li>
      % end
    </ol>
  % else:
    <p class="empty">No activity yet.</p>
  % end
</section>
