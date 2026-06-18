/**
 * Contract Manager v0.0.2 — Vue 3 SPA
 * CDN-loaded Vue 3 + Vue Router (hash mode), dark theme.
 */
'use strict';

const BASE = '/projects/contract-manager-fresh';
const API = BASE + '/api';

// ── API Helper ────────────────────────────────────────────────────────────────

const api = {
    async request(method, url, body) {
        const opts = {
            method,
            headers: {},
            credentials: 'same-origin',
        };
        if (body && !(body instanceof FormData)) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        } else if (body instanceof FormData) {
            opts.body = body;
        }
        try {
            const res = await fetch(API + url, opts);
            const ctype = res.headers.get('content-type') || '';
            if (ctype.includes('application/json')) {
                return await res.json();
            }
            return { ok: res.ok, status: res.status };
        } catch (e) {
            return { ok: false, error: '网络错误: ' + e.message };
        }
    },
    get(url)     { return this.request('GET', url); },
    post(url, b) { return this.request('POST', url, b); },
    put(url, b)  { return this.request('PUT', url, b); },
    del(url)     { return this.request('DELETE', url); },
};

// ── Global State ──────────────────────────────────────────────────────────────

const store = Vue.reactive({
    user: null,
    loading: false,

    async fetchUser() {
        const r = await api.get('/auth/me');
        if (r.ok) {
            this.user = r.user;
        } else {
            this.user = null;
        }
    },

    async logout() {
        await api.post('/auth/logout');
        this.user = null;
    },

    isAdmin() {
        return this.user && this.user.role === 'admin';
    },
});

// ── Login Page ────────────────────────────────────────────────────────────────

const LoginPage = {
    template: /*html*/`
    <div class="login-page">
        <div class="login-card">
            <h1>📋 Contract Manager</h1>
            <h2>用户登录</h2>
            <div v-if="error" class="alert alert-error">{{ error }}</div>
            <form @submit.prevent="doLogin" class="login-form">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input id="username" v-model="username" placeholder="请输入用户名"
                           required autocomplete="username" autofocus>
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input id="password" type="password" v-model="password"
                           placeholder="请输入密码" required autocomplete="current-password">
                </div>
                <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
                    {{ loading ? '登录中...' : '登 录' }}
                </button>
            </form>
            <div class="login-footer">
                <p>演示账号: admin / admin123 &nbsp;|&nbsp; user / user123</p>
            </div>
        </div>
    </div>`,
    data() {
        return {
            username: '',
            password: '',
            error: '',
            loading: false,
        };
    },
    async mounted() {
        await store.fetchUser();
        if (store.user) {
            this.$router.replace('/');
        }
    },
    methods: {
        async doLogin() {
            this.error = '';
            this.loading = true;
            const r = await api.post('/auth/login', {
                username: this.username,
                password: this.password,
            });
            this.loading = false;
            if (r.ok) {
                store.user = r.user;
                this.$router.replace('/');
            } else {
                this.error = r.error || '登录失败';
            }
        },
    },
};

// ── NavBar Component ───────────────────────────────────────────────────────────

const NavBar = {
    template: /*html*/`
    <nav class="navbar">
        <div class="nav-container">
            <router-link to="/" class="nav-brand">📋 Contract Manager</router-link>
            <div class="nav-links">
                <router-link to="/">合同列表</router-link>
                <router-link v-if="store.isAdmin()" to="/users">用户管理</router-link>
                <router-link v-if="store.isAdmin()" to="/audit-logs">操作日志</router-link>
                <span class="nav-user">👤 {{ store.user?.username }} ({{ store.user?.role }})</span>
                <a @click.prevent="doLogout" class="btn-logout" href="#">退出</a>
            </div>
        </div>
    </nav>`,
    setup() {
        return { store };
    },
    methods: {
        async doLogout() {
            await store.logout();
            this.$router.replace('/login');
        },
    },
};

// ── Main Layout (authenticated pages) ─────────────────────────────────────────

const MainLayout = {
    template: /*html*/`
    <div class="app-layout">
        <NavBar />
        <main class="app-main container">
            <router-view />
        </main>
    </div>`,
    components: { NavBar },
};

// ── Dashboard (Contract List) ─────────────────────────────────────────────────

const Dashboard = {
    template: /*html*/`
    <div>
        <div class="page-header">
            <h1>📄 合同列表</h1>
            <router-link to="/contracts/new" class="btn btn-primary">+ 新建合同</router-link>
        </div>
        <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>
        <div v-else-if="error" class="alert alert-error">{{ error }}</div>
        <div v-else-if="contracts.length === 0" class="empty-state">
            <p>暂无合同数据</p>
            <router-link to="/contracts/new" class="btn btn-primary">创建第一份合同</router-link>
        </div>
        <div v-else class="table-wrap">
            <table class="table">
                <thead>
                    <tr>
                        <th>合同编号</th>
                        <th>合同名称</th>
                        <th>甲方</th>
                        <th>乙方</th>
                        <th>金额</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="c in contracts" :key="c.id">
                        <td><code>{{ c.contract_no }}</code></td>
                        <td><router-link :to="'/contracts/' + c.id">{{ c.title }}</router-link></td>
                        <td>{{ c.party_a }}</td>
                        <td>{{ c.party_b || '-' }}</td>
                        <td>{{ c.amount ? '¥' + c.amount.toLocaleString() : '-' }}</td>
                        <td><span :class="'badge badge-' + c.status">{{ c.status }}</span></td>
                        <td>{{ formatDate(c.created_at) }}</td>
                        <td class="actions">
                            <router-link :to="'/contracts/' + c.id" class="btn btn-sm">查看</router-link>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>`,
    data() {
        return { contracts: [], loading: true, error: '' };
    },
    async mounted() { await this.load(); },
    methods: {
        async load() {
            this.loading = true;
            this.error = '';
            const r = await api.get('/contracts');
            this.loading = false;
            if (r.ok) {
                this.contracts = r.contracts;
            } else {
                this.error = r.error || '加载失败';
            }
        },
        formatDate(s) {
            if (!s) return '-';
            return s.slice(0, 10);
        },
    },
};

// ── Contract Detail ───────────────────────────────────────────────────────────

const ContractDetail = {
    template: /*html*/`
    <div>
        <div class="page-header">
            <h1>📝 合同详情</h1>
            <div class="flex gap-1">
                <router-link :to="'/contracts/' + id + '/edit'" class="btn btn-primary btn-sm">编辑</router-link>
                <button @click="showDelete = true" class="btn btn-sm btn-danger">删除</button>
            </div>
        </div>
        <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>
        <div v-else-if="error" class="alert alert-error">{{ error }}</div>
        <div v-else-if="contract">
            <div class="alert" :class="flashType" v-if="flash">{{ flash }}</div>

            <!-- Basic Info -->
            <div class="card">
                <h3>基本信息</h3>
                <div class="detail-grid">
                    <div class="detail-item"><label>合同编号</label><div class="value"><code>{{ contract.contract_no }}</code></div></div>
                    <div class="detail-item"><label>合同名称</label><div class="value">{{ contract.title }}</div></div>
                    <div class="detail-item"><label>甲方</label><div class="value">{{ contract.party_a }}</div></div>
                    <div class="detail-item"><label>乙方</label><div class="value">{{ contract.party_b || '-' }}</div></div>
                    <div class="detail-item"><label>签订日期</label><div class="value">{{ contract.sign_date || '-' }}</div></div>
                    <div class="detail-item"><label>开始日期</label><div class="value">{{ contract.start_date || '-' }}</div></div>
                    <div class="detail-item"><label>结束日期</label><div class="value">{{ contract.end_date || '-' }}</div></div>
                    <div class="detail-item"><label>合同金额</label><div class="value">{{ contract.amount ? '¥' + contract.amount.toLocaleString() : '-' }}</div></div>
                    <div class="detail-item"><label>状态</label><div class="value"><span :class="'badge badge-' + contract.status">{{ contract.status }}</span></div></div>
                    <div class="detail-item"><label>创建人</label><div class="value">{{ contract.creator_name }}</div></div>
                </div>
                <div v-if="contract.remarks" class="mt-2">
                    <label class="text-muted">备注</label>
                    <div class="remarks-value">{{ contract.remarks }}</div>
                </div>
            </div>

            <!-- Status Flow -->
            <div class="card" v-if="contract.valid_transitions && contract.valid_transitions.length > 0">
                <h3>状态流转</h3>
                <p class="text-muted mb-1">当前状态: <span :class="'badge badge-' + contract.status">{{ contract.status }}</span></p>
                <div class="status-flow">
                    <button v-for="s in contract.valid_transitions" :key="s"
                            @click="changeStatus(s)"
                            class="btn btn-sm"
                            :class="statusBtnClass(s)"
                            :disabled="statusLoading">
                        → {{ s }}
                    </button>
                </div>
            </div>

            <!-- Attachments -->
            <div class="card">
                <h3>📎 附件管理</h3>
                <div v-if="attachError" class="alert alert-error">{{ attachError }}</div>
                <div class="upload-area">
                    <p class="text-muted mb-1">上传附件 (PDF / DOC / DOCX, 最大 10MB)</p>
                    <input type="file" ref="fileInput" @change="onFileChange"
                           accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document">
                    <button @click="doUpload" class="btn btn-primary btn-sm mt-1" :disabled="!selectedFile || uploading">
                        {{ uploading ? '上传中...' : '上传附件' }}
                    </button>
                </div>
                <ul v-if="contract.attachments && contract.attachments.length" class="attachment-list">
                    <li v-for="att in contract.attachments" :key="att.id" class="attachment-item">
                        <div class="file-info">
                            <span class="file-icon">{{ fileIcon(att.mime_type) }}</span>
                            <span class="file-name">{{ att.filename }}</span>
                            <span class="file-size">{{ formatSize(att.file_size) }}</span>
                        </div>
                        <div class="flex gap-1">
                            <a :href="BASE + '/api/attachments/' + att.id + '/download'" class="btn btn-sm">下载</a>
                            <button @click="deleteAttachment(att.id)" class="btn btn-sm btn-danger">删除</button>
                        </div>
                    </li>
                </ul>
                <p v-else class="text-muted">暂无附件</p>
            </div>
        </div>

        <!-- Delete Confirmation Modal -->
        <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
            <div class="modal-content">
                <h3>确认删除</h3>
                <p>确定要删除合同 "{{ contract?.title }}" 吗？此操作不可撤销。</p>
                <div class="modal-actions">
                    <button @click="showDelete = false" class="btn">取消</button>
                    <button @click="doDelete" class="btn btn-danger" :disabled="deleting">
                        {{ deleting ? '删除中...' : '确认删除' }}
                    </button>
                </div>
            </div>
        </div>
    </div>`,
    props: ['id'],
    data() {
        return {
            contract: null,
            loading: true,
            error: '',
            flash: '',
            flashType: 'alert-success',
            selectedFile: null,
            uploading: false,
            attachError: '',
            showDelete: false,
            deleting: false,
            statusLoading: false,
            BASE,
        };
    },
    async mounted() { await this.load(); },
    methods: {
        async load() {
            this.loading = true;
            this.error = '';
            const r = await api.get('/contracts/' + this.id);
            this.loading = false;
            if (r.ok) {
                this.contract = r.contract;
            } else {
                this.error = r.error || '合同不存在';
            }
        },
        async changeStatus(target) {
            this.statusLoading = true;
            const r = await api.post('/contracts/' + this.id + '/status', { status: target });
            this.statusLoading = false;
            if (r.ok) {
                this.contract = r.contract;
                this.showFlash('状态已更新: ' + target, 'alert-success');
            } else {
                this.showFlash(r.error || '状态变更失败', 'alert-error');
            }
        },
        statusBtnClass(s) {
            if (s === 'approved' || s === 'active') return 'btn-success';
            if (s === 'terminated') return 'btn-danger';
            if (s === 'pending_review') return 'btn-warning';
            return '';
        },
        onFileChange(e) {
            this.selectedFile = e.target.files[0] || null;
            this.attachError = '';
        },
        async doUpload() {
            if (!this.selectedFile) return;
            this.uploading = true;
            this.attachError = '';
            const fd = new FormData();
            fd.append('file', this.selectedFile);
            const r = await api.request('POST', '/attachments/contracts/' + this.id, fd);
            this.uploading = false;
            if (r.ok) {
                this.selectedFile = null;
                if (this.$refs.fileInput) this.$refs.fileInput.value = '';
                await this.load();
                this.showFlash('附件上传成功', 'alert-success');
            } else {
                this.attachError = r.error || '上传失败';
            }
        },
        async deleteAttachment(attId) {
            if (!confirm('确定删除此附件？')) return;
            const r = await api.del('/attachments/' + attId);
            if (r.ok) {
                await this.load();
                this.showFlash('附件已删除', 'alert-success');
            } else {
                this.showFlash(r.error || '删除失败', 'alert-error');
            }
        },
        async doDelete() {
            this.deleting = true;
            const r = await api.del('/contracts/' + this.id);
            this.deleting = false;
            if (r.ok) {
                this.$router.replace('/');
            } else {
                this.showFlash(r.error || '删除失败', 'alert-error');
                this.showDelete = false;
            }
        },
        showFlash(msg, type) {
            this.flash = msg;
            this.flashType = type;
            setTimeout(() => { this.flash = ''; }, 4000);
        },
        fileIcon(mime) {
            if (mime && mime.includes('pdf')) return '📕';
            if (mime && mime.includes('word')) return '📘';
            return '📄';
        },
        formatSize(bytes) {
            if (!bytes) return '0 B';
            const u = ['B', 'KB', 'MB', 'GB'];
            let i = 0;
            let s = bytes;
            while (s >= 1024 && i < u.length - 1) { s /= 1024; i++; }
            return s.toFixed(i > 0 ? 1 : 0) + ' ' + u[i];
        },
    },
};

// ── Contract Edit / Create ────────────────────────────────────────────────────

const ContractEdit = {
    template: /*html*/`
    <div>
        <div class="page-header">
            <h1>{{ isEdit ? '编辑合同' : '新建合同' }}</h1>
        </div>
        <div v-if="loading && isEdit" class="loading"><span class="spinner"></span>加载中...</div>
        <div v-else-if="error" class="alert alert-error">{{ error }}</div>
        <form v-else @submit.prevent="doSubmit" class="card">
            <h3>合同信息</h3>
            <div class="form-grid">
                <div class="form-group">
                    <label>合同名称 <span class="required">*</span></label>
                    <input v-model="form.title" required placeholder="请输入合同名称">
                </div>
                <div class="form-group">
                    <label>甲方 <span class="required">*</span></label>
                    <input v-model="form.party_a" required placeholder="请输入甲方">
                </div>
                <div class="form-group">
                    <label>乙方</label>
                    <input v-model="form.party_b" placeholder="请输入乙方">
                </div>
                <div class="form-group">
                    <label>签订日期</label>
                    <input type="date" v-model="form.sign_date">
                </div>
                <div class="form-group">
                    <label>开始日期</label>
                    <input type="date" v-model="form.start_date">
                </div>
                <div class="form-group">
                    <label>结束日期</label>
                    <input type="date" v-model="form.end_date">
                </div>
                <div class="form-group">
                    <label>合同金额</label>
                    <input type="number" step="0.01" v-model="form.amount" placeholder="0.00">
                </div>
            </div>
            <div class="form-group">
                <label>备注</label>
                <textarea v-model="form.remarks" rows="3" placeholder="备注信息"></textarea>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary" :disabled="submitting">
                    {{ submitting ? '保存中...' : (isEdit ? '保存修改' : '创建合同') }}
                </button>
                <router-link v-if="isEdit" :to="'/contracts/' + id" class="btn">取消</router-link>
                <router-link v-else to="/" class="btn">取消</router-link>
            </div>
        </form>
    </div>`,
    props: ['id'],
    data() {
        return {
            form: { title: '', party_a: '', party_b: '', sign_date: '', start_date: '', end_date: '', amount: null, remarks: '' },
            loading: false,
            submitting: false,
            error: '',
            isEdit: false,
        };
    },
    async mounted() {
        if (this.id) {
            this.isEdit = true;
            await this.loadContract();
        }
    },
    methods: {
        async loadContract() {
            this.loading = true;
            const r = await api.get('/contracts/' + this.id);
            this.loading = false;
            if (r.ok) {
                const c = r.contract;
                this.form = {
                    title: c.title,
                    party_a: c.party_a,
                    party_b: c.party_b || '',
                    sign_date: c.sign_date || '',
                    start_date: c.start_date || '',
                    end_date: c.end_date || '',
                    amount: c.amount,
                    remarks: c.remarks || '',
                };
            } else {
                this.error = r.error || '合同不存在';
            }
        },
        async doSubmit() {
            this.error = '';
            this.submitting = true;
            let r;
            const body = { ...this.form };
            if (body.amount === '' || body.amount === null) body.amount = null;
            else body.amount = parseFloat(body.amount);
            if (!body.sign_date) delete body.sign_date;
            if (!body.start_date) delete body.start_date;
            if (!body.end_date) delete body.end_date;

            if (this.isEdit) {
                r = await api.put('/contracts/' + this.id, body);
            } else {
                r = await api.post('/contracts', body);
            }
            this.submitting = false;
            if (r.ok) {
                this.$router.replace('/contracts/' + r.contract.id);
            } else {
                this.error = r.error || '保存失败';
            }
        },
    },
};

// ── User List ─────────────────────────────────────────────────────────────────

const UserList = {
    template: /*html*/`
    <div>
        <div class="page-header">
            <h1>👥 用户管理</h1>
            <router-link to="/users/new" class="btn btn-primary">+ 新建用户</router-link>
        </div>
        <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>
        <div v-else-if="error" class="alert alert-error">{{ error }}</div>
        <div v-else class="table-wrap">
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>用户名</th>
                        <th>角色</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="u in users" :key="u.id">
                        <td>{{ u.id }}</td>
                        <td>{{ u.username }}</td>
                        <td><span :class="'badge badge-' + u.role">{{ u.role }}</span></td>
                        <td><span :class="'badge badge-' + u.status">{{ u.status }}</span></td>
                        <td>{{ formatDate(u.created_at) }}</td>
                        <td class="actions">
                            <router-link :to="'/users/' + u.id + '/edit'" class="btn btn-sm">编辑</router-link>
                            <button @click="toggleStatus(u)" class="btn btn-sm btn-warning"
                                    :disabled="store.user?.id === u.id">
                                {{ u.status === 'active' ? '禁用' : '启用' }}
                            </button>
                            <button @click="confirmResetPwd(u)" class="btn btn-sm">重置密码</button>
                            <button @click="confirmDelete(u)" class="btn btn-sm btn-danger"
                                    :disabled="store.user?.id === u.id">删除</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Reset Password Modal -->
        <div v-if="resetTarget" class="modal-overlay" @click.self="resetTarget = null">
            <div class="modal-content">
                <h3>重置密码 — {{ resetTarget.username }}</h3>
                <div class="form-group">
                    <label>新密码</label>
                    <input type="text" v-model="newPassword" placeholder="输入新密码">
                </div>
                <div class="modal-actions">
                    <button @click="resetTarget = null" class="btn">取消</button>
                    <button @click="doResetPwd" class="btn btn-primary" :disabled="!newPassword">确认重置</button>
                </div>
            </div>
        </div>

        <!-- Delete Confirmation Modal -->
        <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
            <div class="modal-content">
                <h3>确认删除</h3>
                <p>确定要删除用户 "{{ deleteTarget.username }}" 吗？</p>
                <div class="modal-actions">
                    <button @click="deleteTarget = null" class="btn">取消</button>
                    <button @click="doDelete" class="btn btn-danger">确认删除</button>
                </div>
            </div>
        </div>
    </div>`,
    setup() {
        return { store };
    },
    data() {
        return {
            users: [], loading: true, error: '',
            resetTarget: null, newPassword: '',
            deleteTarget: null,
        };
    },
    async mounted() { await this.load(); },
    methods: {
        async load() {
            this.loading = true;
            this.error = '';
            const r = await api.get('/users');
            this.loading = false;
            if (r.ok) {
                this.users = r.users;
            } else {
                this.error = r.error || '加载失败';
            }
        },
        async toggleStatus(u) {
            const r = await api.post('/users/' + u.id + '/toggle-status');
            if (r.ok) {
                await this.load();
            } else {
                alert(r.error);
            }
        },
        confirmResetPwd(u) {
            this.resetTarget = u;
            this.newPassword = '';
        },
        async doResetPwd() {
            const r = await api.post('/users/' + this.resetTarget.id + '/reset-password', {
                new_password: this.newPassword,
            });
            if (r.ok) {
                this.resetTarget = null;
                alert('密码已重置');
            } else {
                alert(r.error);
            }
        },
        confirmDelete(u) {
            this.deleteTarget = u;
        },
        async doDelete() {
            const r = await api.del('/users/' + this.deleteTarget.id);
            if (r.ok) {
                this.deleteTarget = null;
                await this.load();
            } else {
                alert(r.error);
            }
        },
        formatDate(s) {
            if (!s) return '-';
            return s.slice(0, 10);
        },
    },
};

// ── User Edit / Create ────────────────────────────────────────────────────────

const UserEdit = {
    template: /*html*/`
    <div>
        <div class="page-header">
            <h1>{{ isEdit ? '编辑用户' : '新建用户' }}</h1>
        </div>
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <form @submit.prevent="doSubmit" class="card">
            <h3>用户信息</h3>
            <div class="form-group">
                <label>用户名 <span class="required">*</span></label>
                <input v-model="form.username" required placeholder="请输入用户名">
            </div>
            <div class="form-group">
                <label>密码 <span v-if="!isEdit" class="required">*</span></label>
                <input type="text" v-model="form.password" :placeholder="isEdit ? '留空则不修改' : '请输入密码'">
            </div>
            <div class="form-group">
                <label>角色</label>
                <select v-model="form.role">
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                </select>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary" :disabled="submitting">
                    {{ submitting ? '保存中...' : (isEdit ? '保存修改' : '创建用户') }}
                </button>
                <router-link to="/users" class="btn">取消</router-link>
            </div>
        </form>
    </div>`,
    props: ['id'],
    data() {
        return {
            form: { username: '', password: '', role: 'user' },
            isEdit: false,
            submitting: false,
            error: '',
        };
    },
    async mounted() {
        if (this.id) {
            this.isEdit = true;
            this.error = '';
            const r = await api.get('/users');
            if (r.ok) {
                const u = r.users.find(x => x.id == this.id);
                if (u) {
                    this.form.username = u.username;
                    this.form.role = u.role;
                    this.form.password = '';
                } else {
                    this.error = '用户不存在';
                }
            } else {
                this.error = r.error || '加载失败';
            }
        }
    },
    methods: {
        async doSubmit() {
            this.error = '';
            this.submitting = true;
            let r;
            const body = {
                username: this.form.username,
                role: this.form.role,
                password: this.form.password,
            };
            if (this.isEdit) {
                r = await api.put('/users/' + this.id, body);
            } else {
                if (!body.password) {
                    this.error = '密码不能为空';
                    this.submitting = false;
                    return;
                }
                r = await api.post('/users', body);
            }
            this.submitting = false;
            if (r.ok) {
                this.$router.replace('/users');
            } else {
                this.error = r.error || '保存失败';
            }
        },
    },
};

// ── Audit Logs ────────────────────────────────────────────────────────────────

const AuditLogs = {
    template: /*html*/`
    <div>
        <div class="page-header">
            <h1>📋 操作日志</h1>
        </div>
        <div v-if="loading" class="loading"><span class="spinner"></span>加载中...</div>
        <div v-else-if="error" class="alert alert-error">{{ error }}</div>
        <div v-else class="table-wrap">
            <table class="table">
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>用户</th>
                        <th>操作</th>
                        <th>目标类型</th>
                        <th>目标ID</th>
                        <th>详情</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="log in logs" :key="log.id" class="audit-log">
                        <td>{{ formatDate(log.created_at) }}</td>
                        <td>{{ log.username }}</td>
                        <td><span :class="'badge badge-' + log.action">{{ log.action }}</span></td>
                        <td>{{ log.target_type }}</td>
                        <td><code>{{ log.target_id }}</code></td>
                        <td class="text-small text-muted">{{ JSON.stringify(log.detail) }}</td>
                    </tr>
                </tbody>
            </table>
            <p v-if="logs.length === 0" class="text-muted">暂无操作日志</p>
        </div>
    </div>`,
    data() {
        return { logs: [], loading: true, error: '' };
    },
    async mounted() { await this.load(); },
    methods: {
        async load() {
            this.loading = true;
            this.error = '';
            const r = await api.get('/audit-logs');
            this.loading = false;
            if (r.ok) {
                this.logs = r.logs;
            } else {
                this.error = r.error || '加载失败';
            }
        },
        formatDate(s) {
            if (!s) return '-';
            return s.replace('T', ' ').slice(0, 19);
        },
    },
};

// ── 404 ───────────────────────────────────────────────────────────────────────

const NotFound = {
    template: `<div style="text-align:center;padding:4rem 1.5rem;">
        <h1 style="font-size:4rem;color:var(--color-text-muted);">404</h1>
        <h2 style="margin-bottom:1rem;color:var(--color-text-muted);">页面未找到</h2>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
    </div>`,
};

// ── Router ────────────────────────────────────────────────────────────────────

const routes = [
    {
        path: '/login',
        component: LoginPage,
    },
    {
        path: '/',
        component: MainLayout,
        meta: { requiresAuth: true },
        children: [
            { path: '', component: Dashboard },
            { path: 'contracts/new', component: ContractEdit },
            { path: 'contracts/:id', component: ContractDetail, props: true },
            { path: 'contracts/:id/edit', component: ContractEdit, props: true },
            { path: 'users', component: UserList, meta: { requiresAdmin: true } },
            { path: 'users/new', component: UserEdit, meta: { requiresAdmin: true } },
            { path: 'users/:id/edit', component: UserEdit, props: true, meta: { requiresAdmin: true } },
            { path: 'audit-logs', component: AuditLogs, meta: { requiresAdmin: true } },
            { path: ':pathMatch(.*)*', component: NotFound },
        ],
    },
];

const router = VueRouter.createRouter({
    history: VueRouter.createWebHashHistory(),
    routes,
    scrollBehavior() {
        return { top: 0 };
    },
});

// ── Auth Guard ────────────────────────────────────────────────────────────────

router.beforeEach(async (to, from, next) => {
    // Fetch user on first navigation if not loaded
    if (!store.user) {
        await store.fetchUser();
    }

    const requiresAuth = to.matched.some(r => r.meta.requiresAuth);
    const requiresAdmin = to.matched.some(r => r.meta.requiresAdmin);

    if (requiresAuth && !store.user) {
        return next('/login');
    }

    if (requiresAdmin && !store.isAdmin()) {
        return next('/');
    }

    // Redirect login to home if already authenticated
    if (to.path === '/login' && store.user) {
        return next('/');
    }

    next();
});

// ── Create App ────────────────────────────────────────────────────────────────

const app = Vue.createApp({});
app.use(router);
app.mount('#app');
