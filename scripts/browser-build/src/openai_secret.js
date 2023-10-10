self.secret = ""
self.org = ""

export function get_openai_secret() {
    return self.secret;
}

export function get_openai_organization() {
    return self.org;
}

export function set_openai_secret(secret) {
    self.secret = secret;
}

export function set_openai_organization(org) {
    self.org = org;
}

self.get_openai_secret = get_openai_secret
self.set_openai_secret = set_openai_secret
self.get_openai_organization = get_openai_organization
self.set_openai_organization = set_openai_organization